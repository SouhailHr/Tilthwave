"""
Reliability basics: database timeouts, idempotent command producer, a breaker on field commands
within a tick, backoff with jitter when the database is down, and the dead-letter topic.
"""

import json
import logging

import pytest
from prometheus_client import REGISTRY

import wiring
from common.exceptions import BrokerError
from infrastructure.exceptions import DBReposException
from infrastructure.repositories.base import engine_options
from interfaces.flow_runner import flow_runner
from interfaces.streamer import run_streamer

helper = flow_runner.ZoneAutomaticIrrigationHelper


def _value(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


# ---- 1. database timeouts -------------------------------------------------------------------


def test_postgres_connections_carry_a_connect_and_a_statement_timeout():
    options = engine_options("postgresql://u:p@db:5432/tilthwave")
    assert options["connect_args"] == {"connect_timeout": 5, "options": "-c statement_timeout=15000"}
    assert options["pool_size"] == 10
    assert engine_options("sqlite:///t.db") == {}  # the test database has no such knobs


# ---- 4. idempotent producer -----------------------------------------------------------------


def test_the_command_producer_is_idempotent():
    assert wiring.producer_config("redpanda:29092") == {
        "bootstrap.servers": "redpanda:29092",
        "enable.idempotence": True,
    }


# ---- 3. breaker within a tick ---------------------------------------------------------------


class _Zone:
    def __init__(self, name):
        self.zone_name = name


class _Zones:
    def __init__(self, names):
        self.zones = [_Zone(n) for n in names]
        self.closed = False

    def filter(self):
        return self.zones

    def get_all_irrigation_tasks(self, task_status):
        return []

    def latest_zone_readings(self, names):
        return {}


class _Sources:
    def __init__(self):
        self.closed = 0

    def close_all_water_sources(self):
        self.closed += 1


def test_a_failed_command_stops_the_rest_of_the_tick(monkeypatch):
    zones, sources = _Zones(["A", "B", "C"]), _Sources()
    monkeypatch.setattr(helper, "zone_use_case", zones)
    monkeypatch.setattr(helper, "water_source_use_case", sources)
    handled = []

    def handle(zone, task, readings):
        handled.append(zone.zone_name)
        raise BrokerError("broker down")

    monkeypatch.setattr(helper, "_handle_zone", staticmethod(handle))
    trips = _value("tilthwave_flow_runner_breaker_trips_total")
    assert helper.auto_irrigation() == 1
    assert handled == ["A"]  # B and C wait for the next tick instead of 5 s each
    assert sources.closed == 0  # closing would also go through the broker
    assert _value("tilthwave_flow_runner_breaker_trips_total") == trips + 1


def test_other_zone_errors_do_not_trip_the_breaker(monkeypatch):
    zones, sources = _Zones(["A", "B"]), _Sources()
    monkeypatch.setattr(helper, "zone_use_case", zones)
    monkeypatch.setattr(helper, "water_source_use_case", sources)
    handled = []

    def handle(zone, task, readings):
        handled.append(zone.zone_name)
        raise ValueError("bad zone config")

    monkeypatch.setattr(helper, "_handle_zone", staticmethod(handle))
    assert helper.auto_irrigation() == 2
    assert handled == ["A", "B"] and sources.closed == 1


# ---- 2. backoff with jitter -----------------------------------------------------------------


def test_retry_delay_doubles_with_jitter_up_to_a_ceiling(monkeypatch):
    monkeypatch.setattr(run_streamer.random, "uniform", lambda low, high: high)
    assert [run_streamer.retry_delay(n) for n in (1, 2, 3, 4, 5, 6, 10)] == [5, 10, 20, 40, 60, 60, 60]
    monkeypatch.setattr(run_streamer.random, "uniform", lambda low, high: low)
    assert run_streamer.retry_delay(3) == 10  # full jitter: between half and the ceiling


def test_the_streamer_backs_off_while_the_database_is_down_and_resets_after(monkeypatch):
    waits = []
    monkeypatch.setattr(run_streamer.time, "sleep", waits.append)
    monkeypatch.setattr(run_streamer.random, "uniform", lambda low, high: high)
    monkeypatch.setattr(run_streamer, "_db_failures", 0)

    def down(event):
        raise DBReposException("connection refused")

    monkeypatch.setattr(run_streamer.event_handler, "process", down)
    for _ in range(3):
        with pytest.raises(run_streamer.NackMessage):
            run_streamer.sensors_streamer({"event_type": "data_record"})
    assert waits == [5, 10, 20]
    assert _value("tilthwave_streamer_retry_delay_seconds") == 20

    monkeypatch.setattr(run_streamer.event_handler, "process", lambda event: None)
    run_streamer.sensors_streamer({"event_type": "data_record"})
    assert run_streamer._db_failures == 0
    assert _value("tilthwave_streamer_retry_delay_seconds") == 0


# ---- 5. dead-letter topic -------------------------------------------------------------------


class _Producer:
    def __init__(self, config, fail=False, unacked=0):
        self.config, self.fail, self.unacked, self.sent = config, fail, unacked, []

    def produce(self, topic, value):
        if self.fail:
            raise RuntimeError("broker gone")
        self.sent.append((topic, json.loads(value)))

    def flush(self, timeout):
        return self.unacked


def test_a_rejected_event_is_parked_on_the_dead_letter_topic(monkeypatch):
    made = []
    monkeypatch.setattr(run_streamer, "_dlq_producer", None)
    monkeypatch.setattr(run_streamer, "Producer", lambda config: made.append(_Producer(config)) or made[-1])
    run_streamer.dead_letter({"event_type": "bogus"}, ValueError("unknown event type"))
    topic, record = made[0].sent[0]
    assert topic == "test.sensors.dlq"
    assert record["event"] == {"event_type": "bogus"}
    assert record["error"] == "ValueError: unknown event type" and record["failed_at"]


@pytest.mark.parametrize("fake", [dict(fail=True), dict(unacked=1)], ids=["produce-raises", "not-acknowledged"])
def test_a_dead_letter_failure_is_logged_not_raised(monkeypatch, caplog, fake):
    monkeypatch.setattr(run_streamer, "_dlq_producer", _Producer({}, **fake))
    with caplog.at_level(logging.ERROR, logger=run_streamer.logger.name):
        run_streamer.dead_letter({"event_type": "bogus"}, ValueError("x"))
    assert "Could not dead-letter the event" in caplog.text and "bogus" in caplog.text

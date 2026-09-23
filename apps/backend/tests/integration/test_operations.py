"""
Operations: the metrics every process exports (common/metrics.py), the API's token-gated
/metrics, and the JSON log format a shipper can index.
"""

import json
import logging
import sys

import pytest
from prometheus_client import REGISTRY

from common.logging import JsonFormatter, configure_logging
from common.request_context import reset_request_id, set_request_id
from config.settings import settings
from infrastructure.exceptions import DBReposException
from infrastructure.repositories.base import BaseBrokerRepo, BrokerError
from interfaces.flow_runner import flow_runner
from interfaces.streamer import run_streamer
from tests.conftest import FARM_A

TOKEN = "scrape-me-9f8e7d6c5b4a3f2e1d0c"


def _value(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


# ---- API -----------------------------------------------------------------------------------------


def test_metrics_endpoint_is_off_without_a_token_and_gated_with_one(client, monkeypatch):
    monkeypatch.setattr(settings.API, "METRICS_TOKEN", None)
    assert client.get("/metrics").status_code == 404

    monkeypatch.setattr(settings.API, "METRICS_TOKEN", TOKEN)
    refused = client.get("/metrics")
    assert refused.status_code == 401 and refused.json()["error_code"] == "unauthenticated"
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.get("/metrics", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200 and ok.headers["content-type"].startswith("text/plain")
    assert "tilthwave_http_requests_total" in ok.text and "tilthwave_flow_runner_ticks_total" in ok.text


def test_requests_are_counted_by_route_template_not_by_path(client, auth_headers, make_farm, make_zone):
    make_farm(FARM_A)
    zone = make_zone("Zone A")
    before = _value("tilthwave_http_requests_total", method="GET", route="/zones/{id}", status="2xx")
    unmatched = _value("tilthwave_http_requests_total", method="GET", route="unmatched", status="4xx")
    client.get(f"/zones/{zone.id}", headers=auth_headers())
    client.get(f"/zones/{zone.id}", headers=auth_headers())
    client.get("/no-such-route", headers=auth_headers())
    assert _value("tilthwave_http_requests_total", method="GET", route="/zones/{id}", status="2xx") == before + 2
    assert _value("tilthwave_http_requests_total", method="GET", route="unmatched", status="4xx") == unmatched + 1
    assert _value("tilthwave_http_request_duration_seconds_count", method="GET", route="/zones/{id}") >= 2


# ---- streamer and flow runner ------------------------------------------------------------------


def test_streamer_counts_each_outcome(monkeypatch):
    monkeypatch.setattr(run_streamer, "DB_RETRY_SECONDS", 0)
    counts = {o: _value("tilthwave_streamer_events_total", outcome=o) for o in ("processed", "nacked", "rejected")}

    monkeypatch.setattr(run_streamer.event_handler, "process", lambda event: None)
    run_streamer.sensors_streamer({"event_type": "data_record"})

    def down(event):
        raise DBReposException("connection refused")

    monkeypatch.setattr(run_streamer.event_handler, "process", down)
    with pytest.raises(run_streamer.NackMessage):
        run_streamer.sensors_streamer({"event_type": "data_record"})

    def bad(event):
        raise ValueError("bogus")

    monkeypatch.setattr(run_streamer.event_handler, "process", bad)
    with pytest.raises(ValueError):
        run_streamer.sensors_streamer({"event_type": "bogus"})

    for outcome in counts:
        assert _value("tilthwave_streamer_events_total", outcome=outcome) == counts[outcome] + 1


def test_flow_runner_ticks_are_counted_and_the_heartbeat_is_a_number(monkeypatch, tmp_path):
    monkeypatch.setattr(flow_runner, "HEARTBEAT_FILE", tmp_path / "hb")
    helper = flow_runner.ZoneAutomaticIrrigationHelper
    ok, failed = (_value("tilthwave_flow_runner_ticks_total", outcome=o) for o in ("ok", "failed"))
    helper._record_tick(failures=0)
    helper._record_tick(failures=2)
    assert _value("tilthwave_flow_runner_ticks_total", outcome="ok") == ok + 1
    assert _value("tilthwave_flow_runner_ticks_total", outcome="failed") == failed + 1
    assert _value("tilthwave_flow_runner_consecutive_failures") == 1
    assert _value("tilthwave_flow_runner_last_successful_tick_timestamp_seconds") > 0


def test_broker_commands_are_counted_by_outcome(repos):
    class Producer:
        def __init__(self, fail):
            self.fail = fail

        def produce(self, topic, key, value, on_delivery):
            if self.fail:
                raise RuntimeError("librdkafka says no")

        def flush(self, timeout):
            return 0

    sent = _value("tilthwave_broker_commands_total", topic="t", outcome="sent")
    failed = _value("tilthwave_broker_commands_total", topic="t", outcome="failed")
    BaseBrokerRepo(producer=Producer(fail=False), random_broker="b").push_event_to_broker("t", "k", {"x": 1})
    with pytest.raises(BrokerError):
        BaseBrokerRepo(producer=Producer(fail=True), random_broker="b").push_event_to_broker("t", "k", {"x": 1})
    assert _value("tilthwave_broker_commands_total", topic="t", outcome="sent") == sent + 1
    assert _value("tilthwave_broker_commands_total", topic="t", outcome="failed") == failed + 1


# ---- logs ----------------------------------------------------------------------------------------


def test_json_log_lines_carry_level_logger_request_id_message_and_traceback():
    formatter = JsonFormatter()
    logger = logging.getLogger("tests.json")
    token = set_request_id("abc123def4567890")
    try:
        record = logger.makeRecord("tests.json", logging.WARNING, __file__, 1, "hello %s", ("world",), None)
        record.request_id = "abc123def4567890"
        line = json.loads(formatter.format(record))
    finally:
        reset_request_id(token)
    assert line["level"] == "WARNING" and line["logger"] == "tests.json" and line["message"] == "hello world"
    assert line["request_id"] == "abc123def4567890" and line["ts"].endswith("+00:00") and "exc" not in line

    try:
        raise ValueError("boom")
    except ValueError:
        record = logger.makeRecord("tests.json", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())
    assert "ValueError: boom" in json.loads(formatter.format(record))["exc"]


def test_configure_logging_picks_the_format_and_adopts_uvicorn(capsys):
    try:
        configure_logging("INFO", "json")
        logging.getLogger("uvicorn.access").info("GET /health 200")
        line = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
        assert line["logger"] == "uvicorn.access" and line["request_id"] == "-"
        assert not logging.getLogger("uvicorn.access").handlers and logging.getLogger("uvicorn.access").propagate
        configure_logging("INFO", "text")
        logging.getLogger("tests.text").info("plain")
        assert "[-] tests.text: plain" in capsys.readouterr().err
    finally:
        configure_logging(settings.LOG_LEVEL, "text")

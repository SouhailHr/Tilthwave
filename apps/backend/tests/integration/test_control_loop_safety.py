"""
The two safety mechanisms the flow runner and the streamer document must actually work:
giving up after MAX_CONSECUTIVE_FAILURES ends the process (APScheduler swallows SystemExit from a
job), and a database outage makes the streamer retry the message instead of skipping it.
"""

import threading
import time
from datetime import UTC, datetime

import pytest
from faststream.exceptions import NackMessage

import interfaces.flow_runner.flow_runner as flow_runner
from core.use_cases.exceptions import UseCaseException
from infrastructure.exceptions import DBReposException
from interfaces.streamer import run_streamer


def _start_in_thread(loop):
    exit_codes = []
    thread = threading.Thread(target=lambda: exit_codes.append(loop.start()), daemon=True)
    thread.start()
    return thread, exit_codes


def test_scheduler_stops_and_the_exit_code_is_1_when_the_loop_gives_up(monkeypatch):
    def tick_that_gave_up():
        raise flow_runner.ControlLoopFailed("3 consecutive failing ticks")

    monkeypatch.setattr(flow_runner.ZoneAutomaticIrrigationHelper, "tick", staticmethod(tick_that_gave_up))
    loop = flow_runner.ControlLoop(next_run_time=datetime.now(UTC))

    thread, exit_codes = _start_in_thread(loop)
    thread.join(timeout=10)

    assert not thread.is_alive(), "the scheduler kept running after the loop gave up"
    assert exit_codes == [1]
    assert not loop.scheduler.running


def test_an_ordinary_failing_tick_does_not_stop_the_scheduler(monkeypatch):
    ticks = []

    def tick_with_the_broker_down():
        ticks.append(1)
        raise RuntimeError("broker down")

    monkeypatch.setattr(flow_runner.ZoneAutomaticIrrigationHelper, "tick", staticmethod(tick_with_the_broker_down))
    loop = flow_runner.ControlLoop(next_run_time=datetime.now(UTC))

    thread, exit_codes = _start_in_thread(loop)
    deadline = time.monotonic() + 5
    while not ticks and time.monotonic() < deadline:
        time.sleep(0.05)
    time.sleep(0.2)  # let the job-error event reach the listener

    assert ticks, "the tick never ran"
    assert loop.scheduler.running
    assert loop.failure is None
    loop.scheduler.shutdown(wait=False)
    thread.join(timeout=10)
    assert exit_codes == [0]


def test_a_tick_that_cannot_list_the_zones_counts_as_a_failure(monkeypatch, tmp_path):
    helper = flow_runner.ZoneAutomaticIrrigationHelper
    monkeypatch.setattr(flow_runner, "HEARTBEAT_FILE", tmp_path / "hb")

    class DatabaseDown:
        def filter(self, *_args, **_kwargs):
            raise DBReposException("connection refused")

    monkeypatch.setattr(helper, "zone_use_case", DatabaseDown())
    helper.tick()

    assert helper.consecutive_failures == 1
    assert not (tmp_path / "hb").exists(), "a failed tick must not refresh the heartbeat"


def test_flow_runner_gives_up_after_consecutive_failures(monkeypatch, tmp_path):
    helper = flow_runner.ZoneAutomaticIrrigationHelper
    monkeypatch.setattr(flow_runner, "HEARTBEAT_FILE", tmp_path / "hb")
    monkeypatch.setattr(flow_runner, "MAX_CONSECUTIVE_FAILURES", 3)

    helper._record_tick(failures=0)
    assert (tmp_path / "hb").exists()
    helper._record_tick(failures=1)
    helper._record_tick(failures=1)
    with pytest.raises(flow_runner.ControlLoopFailed):
        helper._record_tick(failures=1)


def test_database_outage_nacks_the_message_instead_of_skipping_it(monkeypatch):
    def database_down(event):
        raise DBReposException("connection refused")

    monkeypatch.setattr(run_streamer.event_handler, "process", database_down)
    monkeypatch.setattr(run_streamer, "DB_RETRY_SECONDS", 0)

    with pytest.raises(NackMessage):
        run_streamer.sensors_streamer({"event_type": "data_record", "sensor_serial_number": "MSN1"})


def test_a_bad_payload_is_rejected_not_retried():
    with pytest.raises(UseCaseException):
        run_streamer.sensors_streamer({"event_type": "bogus"})

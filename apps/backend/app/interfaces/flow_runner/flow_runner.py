"""
Flow runner: the irrigation control loop.

Every FLOW_RUNNER_MINUTES it looks at each zone's latest readings and starts or stops irrigation
against the zone's triggers. Two safety rules override the triggers (see FlowRunnerSettings):
  - a task running longer than MAX_IRRIGATION_MINUTES is force-stopped,
  - a zone whose latest reading is older than MAX_READING_AGE_MINUTES is "blind": it never starts
    and, if irrigating, is stopped. A dead sensor feed can therefore not leave a valve open.

This process is the only one wired with a real broker gateway (wiring.worker_use_cases): commands
are published before the task state is persisted, and a failed publish aborts the state change.
"""

import logging
import pathlib
import signal
import sys

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.blocking import BlockingScheduler

import common.constants as global_constants
from common.dates import minutes_since
from common.logging import configure_logging
from config.settings import settings
from wiring import worker_use_cases

logger = logging.getLogger(__name__)

# Touched after every successful tick; the container healthcheck fails when it goes stale.
HEARTBEAT_FILE = pathlib.Path("/tmp/flow-runner.heartbeat")
# Consecutive failed ticks before the process exits and lets the restart policy take over.
MAX_CONSECUTIVE_FAILURES = 10


class ControlLoopFailed(RuntimeError):
    """MAX_CONSECUTIVE_FAILURES ticks failed in a row; the process must end (see ControlLoop)."""


class ZoneAutomaticIrrigationHelper:
    """
    The control loop. Use cases are injected with configure() (a real broker gateway in run(),
    a recording one in tests) so importing this module never opens a Kafka producer.
    """

    STOP = "stop"
    START = "start"

    zone_use_case = None
    irrigation_task_use_case = None
    water_source_use_case = None
    consecutive_failures = 0

    @classmethod
    def configure(cls, use_cases):
        cls.zone_use_case = use_cases.zone
        cls.irrigation_task_use_case = use_cases.irrigation_task
        cls.water_source_use_case = use_cases.water_source

    @classmethod
    def _get_value_from_sensors_record(cls, sensors_records, value):
        """
        @param sensors_records: [{"type": "moisture", "value": 30, "recorded_at": "..."}, ...]
        @param value: the reading type wanted
        @return: the reading value or None
        """
        record_dict = {record["type"]: record["value"] for record in sensors_records}
        return record_dict.get(value)

    @classmethod
    def _readings_are_stale(cls, zone_name, sensors_records) -> bool:
        """
        True when any of the zone's latest readings is older than MAX_READING_AGE_MINUTES.
        """
        max_age = settings.FLOW_RUNNER.MAX_READING_AGE_MINUTES
        oldest = max((minutes_since(record["recorded_at"]) for record in sensors_records), default=None)
        if oldest is not None and oldest > max_age:
            logger.warning(
                "Zone %s is blind: latest reading is %.0f min old (limit %d min)", zone_name, oldest, max_age
            )
            return True
        return False

    @classmethod
    def start_irrigation(cls, zone):
        """
        Start an irrigation task for the Zone
        @param zone: the Zone entity
        @return: the irrigation task
        """
        zone_name = zone.zone_name
        logger.info("Starting Irrigation for %s", zone_name)
        irrigation_task = cls.zone_use_case.start_irrigation(zone_name=zone_name)
        logger.info("Irrigation started id: %s", irrigation_task.id)
        return irrigation_task

    @classmethod
    def stop_irrigation(cls, zone, task_to_stop, reason="stop trigger reached"):
        zone_name = zone.zone_name
        logger.info("Stopping Irrigation for %s (task %s, %s)", zone_name, task_to_stop.id, reason)
        cls.zone_use_case.stop_irrigation(task_in_progress=task_to_stop)

    @classmethod
    def _check_start_stop(cls, zone, task_in_progress, zone_sensors_records=None):
        """
        Decide whether irrigation must be started or stopped for the zone.
        Logic:
            1- hard limits: max runtime, stale readings
            2- zone triggers against the latest moisture and saturation
        @param zone: the Zone entity
        @param task_in_progress: the zone's irrigation task in progress, or None
        @param zone_sensors_records: the zone's latest readings, as the tick fetched them for
               every zone at once; None fetches this zone's own
        @return: (str START | STOP | None, reason)
        """
        zone_name = zone.zone_name
        logger.info("Checking %s ........", zone_name)

        if task_in_progress is not None:
            running_for = cls.irrigation_task_use_case.get_task_in_progress_duration(task_in_progress)
            if running_for >= settings.FLOW_RUNNER.MAX_IRRIGATION_MINUTES:
                return cls.STOP, f"hard stop: running for {running_for} min"

        if zone_sensors_records is None:
            zone_sensors_records = cls.zone_use_case.get_latest_zone_data(zone_name=zone_name)
        current_saturation = cls._get_value_from_sensors_record(zone_sensors_records, "saturation")
        current_moisture = cls._get_value_from_sensors_record(zone_sensors_records, "moisture")
        logger.info(
            "Current values for %s :  Moisture = %s | Saturation = %s", zone_name, current_moisture, current_saturation
        )

        blind = (
            current_saturation is None
            or current_moisture is None
            or cls._readings_are_stale(zone_name, zone_sensors_records)
        )
        if blind:
            if task_in_progress is not None:
                return cls.STOP, "no fresh readings"
            logger.error("Zone %s has missing or stale sensor data; not starting.", zone_name)
            return None, None

        if task_in_progress is None and cls.zone_use_case.check_start_irrigation(
            moisture=current_moisture, saturation=current_saturation, zone=zone
        ):
            return cls.START, "start trigger reached"
        if task_in_progress is not None and cls.zone_use_case.check_stop_irrigation(
            moisture=current_moisture, saturation=current_saturation, zone=zone
        ):
            return cls.STOP, "stop trigger reached"
        return None, None

    @classmethod
    def _handle_zone(cls, zone, task_in_progress, zone_sensors_records):
        condition, reason = cls._check_start_stop(zone, task_in_progress, zone_sensors_records)
        if condition == cls.START:
            cls.start_irrigation(zone=zone)
        elif condition == cls.STOP:
            cls.stop_irrigation(zone=zone, task_to_stop=task_in_progress, reason=reason)

    @classmethod
    def auto_irrigation(cls) -> int:
        """
        One control-loop tick: for each zone, start or stop irrigation as needed, then close the
        water sources when nothing is irrigating.

        A failure in one zone (e.g. the broker is down) is logged and must not prevent the other
        zones from being evaluated; the next tick retries.
        @return: how many steps of this tick failed
        """
        failures = 0
        zones = cls.zone_use_case.filter()
        # Everything a zone's evaluation reads is fetched once for all zones: the open tasks
        # (one query) and the latest reading of every zone sensor (two). A tick is then a fixed
        # handful of queries plus the commands it actually sends, not O(zones x sensors).
        open_tasks = cls.zone_use_case.get_all_irrigation_tasks(
            task_status=global_constants.IRRIGATION_TASK_IN_PROGRESS
        )
        task_by_zone: dict = {}
        for task in open_tasks:
            task_by_zone.setdefault(task.zone_name, task)  # oldest first, as the per-zone query returned
        readings = cls.zone_use_case.latest_zone_readings([zone.zone_name for zone in zones])
        for zone in zones:
            name = zone.zone_name
            try:
                cls._handle_zone(zone, task_by_zone.get(name), readings.get(name, []))
            except Exception:
                failures += 1
                logger.exception("Could not evaluate zone %s", zone.zone_name)

        if not cls.zone_use_case.get_all_irrigation_tasks(task_status=global_constants.IRRIGATION_TASK_IN_PROGRESS):
            try:
                cls.water_source_use_case.close_all_water_sources()
            except Exception:
                failures += 1
                logger.exception("Could not close all water sources; retrying next tick")

        return failures

    @classmethod
    def tick(cls) -> None:
        """
        The scheduled job: one tick plus the failure accounting.

        A tick with any failure does not refresh the heartbeat, so a broken loop goes stale for
        the container healthcheck; MAX_CONSECUTIVE_FAILURES failed ticks in a row raise
        ControlLoopFailed, which ControlLoop turns into a process exit. A failure before any zone
        could be evaluated (the database is down, so listing the zones raised) is a failed tick
        like any other and counts the same way.
        """
        try:
            failures = cls.auto_irrigation()
        except Exception:
            failures = 1
            logger.exception("Tick failed before the zones could be evaluated")
        cls._record_tick(failures)

    @classmethod
    def _record_tick(cls, failures: int) -> None:
        if failures == 0:
            cls.consecutive_failures = 0
            HEARTBEAT_FILE.touch()
            return
        cls.consecutive_failures += 1
        if cls.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            raise ControlLoopFailed(f"{cls.consecutive_failures} consecutive failing ticks")


class ControlLoop:
    """
    The scheduler around the tick, plus the one thing APScheduler will not do for us: end the
    process when the loop gives up.

    A job that raises SystemExit stops nothing: the executor catches BaseException, logs "Job
    raised an exception" and schedules the next run, so an exit inside the tick leaves the
    container unhealthy but alive, forever. Instead the tick raises ControlLoopFailed, the
    EVENT_JOB_ERROR listener below stops the scheduler, start() returns and run() exits non-zero,
    which is what the restart policy reacts to. Any other exception from a tick is one bad tick:
    already logged, retried on the next run.
    """

    def __init__(self, scheduler_cls=BlockingScheduler, **job_options):
        self.failure: ControlLoopFailed | None = None
        self.scheduler = scheduler_cls()
        self.scheduler.add_job(
            ZoneAutomaticIrrigationHelper.tick,
            "interval",
            minutes=settings.FLOW_RUNNER.MINUTES,
            max_instances=1,
            coalesce=True,
            **job_options,
        )
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

    def _on_job_error(self, event) -> None:
        if not isinstance(event.exception, ControlLoopFailed):
            return
        self.failure = event.exception
        logger.critical("%s; stopping so the container restarts", event.exception)
        self.scheduler.shutdown(wait=False)

    def start(self) -> int:
        """Blocks until the scheduler stops. Returns the process exit code."""
        self.scheduler.start()
        return 1 if self.failure else 0


def run():
    configure_logging(settings.LOG_LEVEL)
    ZoneAutomaticIrrigationHelper.configure(worker_use_cases())
    logger.info("................ Starting Flow Runner (every %s min) .........", settings.FLOW_RUNNER.MINUTES)
    loop = ControlLoop()

    def shutdown(signum, _frame):
        logger.info("Received signal %s, shutting down the scheduler", signum)
        loop.scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    sys.exit(loop.start())  # blocks until shutdown; no busy loop


if __name__ == "__main__":
    run()

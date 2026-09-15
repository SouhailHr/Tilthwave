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
        @param zone: Zone data
        @return: the irrigation task
        """
        zone_name = zone.get("zone_name")
        logger.info("Starting Irrigation for %s", zone_name)
        irrigation_task = cls.zone_use_case.start_irrigation(zone_name=zone_name)
        logger.info("Irrigation started id: %s", irrigation_task.id)
        return irrigation_task

    @classmethod
    def stop_irrigation(cls, zone, task_to_stop, reason="stop trigger reached"):
        zone_name = zone.get("zone_name")
        logger.info("Stopping Irrigation for %s (task %s, %s)", zone_name, task_to_stop.id, reason)
        cls.zone_use_case.stop_irrigation(task_in_progress=task_to_stop)

    @classmethod
    def _check_start_stop(cls, zone, task_in_progress):
        """
        Decide whether irrigation must be started or stopped for the zone.
        Logic:
            1- hard limits: max runtime, stale readings
            2- zone triggers against the latest moisture and saturation
        @param zone: A dict that contains a Zone data
        @param task_in_progress: the zone's irrigation task in progress, or None
        @return: (str START | STOP | None, reason)
        """
        zone_name = zone.get("zone_name")
        logger.info("Checking %s ........", zone_name)

        if task_in_progress is not None:
            running_for = cls.irrigation_task_use_case.get_task_in_progress_duration(task_in_progress)
            if running_for >= settings.FLOW_RUNNER.MAX_IRRIGATION_MINUTES:
                return cls.STOP, f"hard stop: running for {running_for} min"

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
    def _handle_zone(cls, zone):
        tasks_in_progress = (
            cls.zone_use_case.get_irrigation_tasks(
                zone_name=zone.get("zone_name"), task_status=global_constants.IRRIGATION_TASK_IN_PROGRESS
            )
            or []
        )
        task_in_progress = tasks_in_progress[0] if tasks_in_progress else None
        condition, reason = cls._check_start_stop(zone, task_in_progress)
        if condition == cls.START:
            cls.start_irrigation(zone=zone)
        elif condition == cls.STOP:
            cls.stop_irrigation(zone=zone, task_to_stop=task_in_progress, reason=reason)

    @classmethod
    def auto_irrigation(cls):
        """
        One control-loop tick: for each zone, start or stop irrigation as needed, then close the
        water sources when nothing is irrigating.

        A failure in one zone (e.g. the broker is down) is logged and must not prevent the other
        zones from being evaluated; the next tick retries. A tick with any failure does not
        refresh the heartbeat, and MAX_CONSECUTIVE_FAILURES failed ticks in a row end the process,
        so a broken loop is visible to the container healthcheck and restart policy instead of
        logging forever while a valve may be open.
        """
        failures = 0
        zones = [zone.to_dict() for zone in cls.zone_use_case.filter()]
        for zone in zones:
            try:
                cls._handle_zone(zone)
            except Exception:
                failures += 1
                logger.exception("Could not evaluate zone %s", zone.get("zone_name"))

        if not cls.zone_use_case.get_all_irrigation_tasks(task_status=global_constants.IRRIGATION_TASK_IN_PROGRESS):
            try:
                cls.water_source_use_case.close_all_water_sources()
            except Exception:
                failures += 1
                logger.exception("Could not close all water sources; retrying next tick")

        cls._record_tick(failures)

    @classmethod
    def _record_tick(cls, failures: int) -> None:
        if failures == 0:
            cls.consecutive_failures = 0
            HEARTBEAT_FILE.touch()
            return
        cls.consecutive_failures += 1
        if cls.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            logger.critical("%d consecutive failing ticks; exiting so the container restarts", cls.consecutive_failures)
            sys.exit(1)


def run():
    configure_logging(settings.LOG_LEVEL)
    ZoneAutomaticIrrigationHelper.configure(worker_use_cases())
    logger.info("................ Starting Flow Runner (every %s min) .........", settings.FLOW_RUNNER.MINUTES)
    scheduler = BlockingScheduler()
    scheduler.add_job(
        ZoneAutomaticIrrigationHelper.auto_irrigation,
        "interval",
        minutes=settings.FLOW_RUNNER.MINUTES,
        max_instances=1,
        coalesce=True,
    )

    def shutdown(signum, _frame):
        logger.info("Received signal %s, shutting down the scheduler", signum)
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    scheduler.start()  # blocks until shutdown; no busy loop


if __name__ == "__main__":
    run()

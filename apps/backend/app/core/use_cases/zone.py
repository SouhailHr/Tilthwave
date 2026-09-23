import logging
from datetime import timedelta

import common.constants as global_constants
from adapters.irrigation_task import IrrigationTaskAdaptor
from common.dates import command_timestamp, utc_now
from config.settings import settings
from core.entities.zone import Zone as ZoneEntity
from core.use_cases.base import BaseUseCase
from core.use_cases.exceptions import UseCaseException

logger = logging.getLogger(__name__)


class ZoneUseCase(BaseUseCase):
    """
    Zones and their irrigation. Collaborators are injected from the composition root (wiring.py):
    this class never builds another use case.
    """

    ENTITY = ZoneEntity

    def __init__(self, repo, irrigation_tasks, water_switchers, water_sources, sensor_records, zone_sensors):
        super().__init__(repo)
        self.irrigation_task_use_case = irrigation_tasks
        self.water_switcher_use_case = water_switchers
        self.water_source_use_case = water_sources
        self.sensor_record_use_case = sensor_records
        self.zone_sensors_use_case = zone_sensors

    @staticmethod
    def check_start_irrigation(moisture: int, saturation: int, zone):
        """
        Check if irrigation needs to be started based on the current moisture and saturation levels.

        Logic:
            1. If both the current saturation is less than or equal to the trigger saturation
               and the current moisture is less than or equal to the trigger moisture, return True.
            2. Otherwise, return False.
            3. if the triggers are missing log an error and return False

        @param moisture: int - The current moisture level of the zone.
        @param saturation: int - The current saturation level of the zone.
        @param zone: the Zone entity - A dictionary representing the zone, which should contain the keys
         'moisture_trigger_start' and 'saturation_trigger_start'.
        @return: bool - True if irrigation needs to be started, False otherwise.
        """
        moisture_trigger_start = zone.moisture_trigger_start
        saturation_trigger_start = zone.saturation_trigger_start

        # Ensure moisture_trigger_start and saturation_trigger_start are not None
        if moisture_trigger_start is None or saturation_trigger_start is None:
            logger.error(f"Zone {zone.zone_name} has missing triggers data.")
            return False

        return saturation <= saturation_trigger_start and moisture <= moisture_trigger_start

    @staticmethod
    def check_stop_irrigation(moisture: int, saturation: int, zone):
        """
        Check if irrigation needs to be stopped based on the current moisture and saturation levels.

        Logic:
            1. If both the current saturation is greater than or equal to the trigger saturation stop
               and the current moisture is greater than or equal to the trigger moisture stop, return True.
            2. Otherwise, return False.
            3. if the triggers are missing log an error and return False

        @param moisture: int - The current moisture level of the zone.
        @param saturation: int - The current saturation level of the zone.
        @param zone: the Zone entity - A dictionary representing the zone, which should contain the keys
         'moisture_trigger_stop' and 'saturation_trigger_stop'.
        @return: bool - True if irrigation needs to be stopped, False otherwise.
        """
        moisture_trigger_stop = zone.moisture_trigger_stop
        saturation_trigger_stop = zone.saturation_trigger_stop
        # Ensure moisture_trigger_stop and saturation_trigger_stop are not None
        if moisture_trigger_stop is None or saturation_trigger_stop is None:
            logger.error(f"Zone {zone.zone_name} has missing triggers data.")
            return False

        return saturation >= saturation_trigger_stop and moisture >= moisture_trigger_stop

    def get_all_irrigation_tasks(self, task_status: str) -> list:
        """Every irrigation task with `task_status`, oldest first; [] when there are none."""
        return self.irrigation_task_use_case.filter(
            filters=[{"attribute": "status", "value": task_status, "condition": "eq"}]
        )

    def start_irrigation(self, zone_name: str):
        """
        Start an irrigation task for the zone: open the water source(s) and switchers (commands
        to the field), and only then record a task "in progress". The order matters: a task is
        recorded once the commands were acknowledged by the broker, so the database never claims
        an irrigation the field never received.
        @return: the created irrigation task
        @raises BrokerError: when a command could not be delivered; no task is created
        """
        self._open_water_switchers(zone_name=zone_name)
        data = {
            "zone_name": zone_name,
            "status": global_constants.IRRIGATION_TASK_IN_PROGRESS,
        }
        task_entity = IrrigationTaskAdaptor.dict_to_entity(data)
        return self.irrigation_task_use_case.create(entity=task_entity)

    def stop_irrigation(self, task_in_progress):
        """
        Stops an irrigation task in progress for a given zone.
        Logic:
            1- Close the zone's water switchers (commands to the field)
            2- Only then mark the task 'completed' and record its duration
        @param task_in_progress: An object representing the irrigation task that is currently in progress.
        @return: the updated irrigation task
        @raises BrokerError: when a command could not be delivered; the task stays in progress
                             so the next run retries the stop
        """
        self._stop_water_switchers(zone_name=task_in_progress.zone_name)
        duration = self.irrigation_task_use_case.get_task_in_progress_duration(task_in_progress=task_in_progress)
        data = {"status": global_constants.IRRIGATION_TASK_COMPLETED, "duration": duration}
        return self.irrigation_task_use_case.update(id=task_in_progress.id, data=data)

    def latest_zone_readings(self, zone_names) -> dict:
        """
        The latest reading of every sensor of every given zone, in two queries for all zones
        together (the zone->sensor links, then the newest record per sensor), instead of one
        link query per zone plus one record query per sensor. The flow runner asks this once per
        tick for every zone it evaluates.
        @return: {zone_name: [{"type", "value", ..., "recorded_at"}, ...]}; zones without a
                 fresh reading are absent
        """
        zone_names = list(zone_names)
        if not zone_names:
            return {}
        links = self.zone_sensors_use_case.filter(
            filters=[{"attribute": "zone_name", "value": zone_names, "condition": "in"}]
        )
        serials = sorted({link.sensor_serial_number for link in links})
        # Only readings the freshness rule would accept: anything older makes the zone blind
        # either way, and the bound keeps the scan to one index range per sensor.
        since = utc_now() - timedelta(minutes=settings.FLOW_RUNNER.MAX_READING_AGE_MINUTES)
        latest = {
            record.sensor_serial_number: record
            for record in self.sensor_record_use_case.latest_per_sensor(serials, since=since)
        }
        readings: dict = {}
        for link in links:
            record = latest.get(link.sensor_serial_number)
            if record:
                readings.setdefault(link.zone_name, []).append({**record.data, "recorded_at": record.created_date})
        return readings

    def get_latest_zone_data(self, zone_name: str):
        """
         This method gets the zone latest sensor records
        @param zone_name: str representing a zone by its name
        @return: List of dict of type, value and recorded_at (UTC, when the record was stored),
        eg :
        [{"type": "saturation", "value": 20, "recorded_at": "2026-09-15 16:07:14.123"}, ...]
        """
        return self.latest_zone_readings([zone_name]).get(zone_name, [])

    def get_zone_water_switchers(self, zone_name: str):
        """
         This method gets all water switchers of a specific zone by the zone name
         logic :
            1- get all the entities of water switchers
            2- extract only the serial_numbers from water switchers data and return water switchers list
        @param zone_name: str representing a zone by its name
        @return: list of water switchers serial numbers
        """
        filter_by = [{"attribute": "zone_name", "value": zone_name, "condition": "eq"}]

        return self.water_switcher_use_case.filter(filters=filter_by)

    @staticmethod
    def _switcher_command(water_switcher, status: str) -> dict:
        """Command payload asking a water switcher's actuator to switch to `status`."""
        return {
            "sensor_serial_number": water_switcher.sensor_serial_number,
            "data": {
                "type": "switcher",
                "status": status,
                "timestamp": command_timestamp(),
            },
        }

    def _open_water_source(self, water_switcher):
        """
        this method opens the water source feeding the given water_switcher, if it is Off
        @param water_switcher:
        @raises BrokerError: when the command could not be delivered
        """
        filter_by = [
            {"attribute": "serial_number", "value": water_switcher.water_source_serial_number, "condition": "eq"},
        ]
        # a switcher is linked to exactly one water source
        water_source = self.water_source_use_case.first(filters=filter_by)
        if water_source is None:
            raise UseCaseException(
                class_name=self.__class__.__name__,
                message=f"water switcher {water_switcher.serial_number} references unknown "
                f"water source {water_switcher.water_source_serial_number}",
            )
        if water_source.status == global_constants.STATUS_OFF:
            self.water_source_use_case.send_event(
                topic=settings.STREAMER.WATER_CONTROL_TOPIC,
                key="water_control_data",
                payload=self.water_source_use_case.build_status_command(water_source, global_constants.STATUS_ON),
            )

    def _open_water_switchers(self, zone_name: str):
        """
        This method opens the water source(s) then the water switchers of a specific zone
        @param zone_name: str representing a zone by its name
        @raises BrokerError: when a command could not be delivered
        """
        for water_switcher in self.get_zone_water_switchers(zone_name=zone_name):
            self._open_water_source(water_switcher=water_switcher)
            self.water_switcher_use_case.send_event(
                topic=settings.STREAMER.WATER_CONTROL_TOPIC,
                key="water_control_data",
                payload=self._switcher_command(water_switcher, global_constants.STATUS_ON),
            )

    def _stop_water_switchers(self, zone_name: str):
        """
        This method closes the water switchers of a specific zone
        @param zone_name: str representing a zone by its name
        @raises BrokerError: when a command could not be delivered
        """
        for water_switcher in self.get_zone_water_switchers(zone_name=zone_name):
            self.water_switcher_use_case.send_event(
                topic=settings.STREAMER.WATER_CONTROL_TOPIC,
                key="water_control_data",
                payload=self._switcher_command(water_switcher, global_constants.STATUS_OFF),
            )

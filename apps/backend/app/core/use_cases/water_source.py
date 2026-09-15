import logging
from collections import defaultdict

from common import constants as global_constants
from common.dates import command_timestamp, parse_db_datetime, utc_now
from config.settings import settings
from core.entities.water_source import WaterSource as WaterSourceEntity
from core.use_cases.base import BaseUseCase
from core.use_cases.exceptions import UseCaseException
from core.use_cases.sensor import SensorUseCase
from core.use_cases.sensor_record import SensorRecordUseCase

logger = logging.getLogger(__name__)


class WaterSourceUseCase(BaseUseCase):
    ENTITY = WaterSourceEntity

    def __init__(self, repo, sensor_repo, sensor_record_repo, broker_repo=None):
        """
        Initialize the use case with a repository.
        we are passing sensor_repo to handle validation
        of the sensor_type

        @param repo: Repository instance handling data operations.
        @param sensor_repo: Repository instance handling data operations for sensor entity
        @param sensor_record_repo: Repository instance handling data operations for sensor records entity
        @param broker_repo: Repository instance handling communication with broker

        """
        super().__init__(repo)
        self.sensor_repo = sensor_repo
        self.broker_repo = broker_repo
        self.sensor_record_repo = sensor_record_repo
        self.sensor_record_use_case = SensorRecordUseCase(repo=self.sensor_record_repo)

    def create(self, entity: ENTITY):
        """
        Create a water source entity using the repository.
        logic:
        1- get the sensor using serial_number
        2- verify sensor type == source_sensor
        3- raise exception if rule is not respected

        @param entity: Entity instance to be created.
        @return: The created entity.
        """
        filter_by = [{"attribute": "serial_number", "value": entity.sensor_serial_number, "condition": "eq"}]
        if entity.sensor_serial_number:
            sensor_use_case = SensorUseCase(repo=self.sensor_repo)
            sensor = sensor_use_case.filter(filters=filter_by)
            if sensor and sensor[0].type == global_constants.SOURCE_SENSOR:
                return self.repo.create(entity)
            raise UseCaseException(
                class_name=self.__class__.__name__,
                message=f"water source can only have a sensor of type {global_constants.SOURCE_SENSOR} ",
            )
        return self.repo.create(entity)

    def update(self, id: int, data: dict):
        """
            Update a water source entity using the repository.
        logic:
        1- Verify if the sensor_serial_number exists in the data if yes do 2 - 3 - 4
        1- get the sensor using serial_number
        2- verify sensor type == source_sensor
        3- raise exception if rule is not respected

        @param id: ID of the entity to update.
        @param data: Dictionary of data to update.
        @return: The updated entity.
        """
        if data.get("sensor_serial_number"):
            sensor_serial_number = data["sensor_serial_number"]
            filter_by = [{"attribute": "serial_number", "value": sensor_serial_number, "condition": "eq"}]
            sensor_use_case = SensorUseCase(repo=self.sensor_repo)
            sensor = sensor_use_case.filter(filters=filter_by)
            if sensor and sensor[0].type == global_constants.SOURCE_SENSOR:
                return self.repo.update(id, data)
            raise UseCaseException(
                class_name=self.__class__.__name__,
                message=f"water source can only have a sensor of type {global_constants.SOURCE_SENSOR}",
            )

        return self.repo.update(id, data)

    def update_by_serial_number(self, serial_number, data: dict):
        """
        Update a water source by serial number.
        logic :
            If the water_source exist update it with the given data
            else remove the sensor serial number from the water source.
        @param serial_number: Serial number of the water source.
        @param data: Dictionary of data to update.
        @return: The updated entity.
        """
        # get the water source using the serial_number
        source_filter_by = [{"attribute": "serial_number", "value": serial_number, "condition": "eq"}]
        water_sources = self.repo.filter(filters=source_filter_by)
        if water_sources:
            # Update the water source with the provided data
            return self.repo.update(water_sources[0].id, data)
        else:
            # Remove the sensor serial number from the water source
            sensor_serial_number = data["sensor_serial_number"]
            filter_by_sensor = [{"attribute": "sensor_serial_number", "value": sensor_serial_number, "condition": "eq"}]
            water_sources = self.filter(filters=filter_by_sensor)
            sensor_data = {"sensor_serial_number": None}
            if water_sources:
                return self.repo.update(water_sources[0].id, sensor_data)

    def update_by_sensor_serial_number(self, sensor_serial_number, data: dict):
        """
        Update a water source by sensor serial number.
        logic :
            If the water_source exist update it with the given data
        @param sensor_serial_number: Serial number of the sensor assigned to the water source .
        @param data: Dictionary of data to update.
        @return: The updated entity.
        """
        # get the water source using the serial_number
        source_filter_by = [{"attribute": "sensor_serial_number", "value": sensor_serial_number, "condition": "eq"}]
        water_sources = self.repo.filter(filters=source_filter_by)
        if water_sources:
            # Update the water source with the provided data
            return self.repo.update(water_sources[0].id, data)
        else:
            logger.info(f"no water source found assigned to the sensor {sensor_serial_number}")

    def close_all_water_sources(self):
        """
        Close all water sources in the farm that are currently On.
        logic:
            - Prepare the payload and send the event using the broker_repo
        @raises BrokerError: if a close command could not be delivered (the caller decides
                             whether to retry; the source may still be open)
        """
        for water_source in self.filter():
            if water_source.sensor_serial_number and water_source.status == global_constants.STATUS_ON:
                self.send_event(
                    topic=settings.STREAMER.WATER_CONTROL_TOPIC,
                    key="water_control_data",
                    payload=self.build_status_command(water_source, global_constants.STATUS_OFF),
                )

    @staticmethod
    def build_status_command(water_source, status: str) -> dict:
        """
        Command payload asking the water source's actuator to switch to `status`.
        """
        return {
            "sensor_serial_number": water_source.sensor_serial_number,
            "data": {
                "type": "source",
                "status": status,  # operational status
                "timestamp": command_timestamp(),
            },
        }

    def get_water_consumption_for_the_year_by_month(self, sensor_serial_number: str):
        """
        Get the water consumption of the year for the water source by month.

        Logic:
        1. Get the water source records.
        2. Filter by the current year.
        3. Extract the total consumption for the water source for each month.

        @param sensor_serial_number: Serial number of the sensor.
        @return: Dictionary with water consumption per month.
        """
        filter_by = [{"attribute": "sensor_serial_number", "value": sensor_serial_number, "condition": "eq"}]
        current_year = utc_now().year
        records = self.sensor_record_repo.filter(filters=filter_by)

        # Dictionary to store consumption per month
        monthly_consumption = defaultdict(int)

        for record in records:
            record_date = parse_db_datetime(record.created_date)
            if record_date.year == current_year:
                month = record_date.month
                consumption = record.data.get("consumption", 0)
                monthly_consumption[month] += consumption

        # Convert default dict to a regular dictionary and ensure all months are present
        consumption_per_month = {month: monthly_consumption.get(month, 0) for month in range(1, 13)}

        return consumption_per_month

    def get_all_water_sources(self):
        """
        this method gets all water sources
        @return: list of water sources
        """

        water_sources = self.filter()
        return water_sources

    @staticmethod
    def check_if_water_sources_are_assigned(water_sources: list):
        """
        This method checks if the water_sources are assigned or not :
        logic:
        1- loop over all water_sources and check if each water_sources is assigned to a sensor
        2 - if assigned add it to, assigned values
        3-  else add to non-assigned values
        4- return the dict
        @param water_sources: list of water_sources
        @return: a dict that has two keys assigned and non-assigned and their values are sensors
        """
        assigned_dict = {"assigned": [], "non-assigned": []}
        for water_source in water_sources:
            sensor = water_source.sensor_serial_number
            if sensor:
                assigned_dict["assigned"].append(water_source)
            else:
                assigned_dict["non-assigned"].append(water_source)
        return assigned_dict

    def get_stats(self):
        """
        this method gets the water sources stats
        @return: dict
            {
                "total_water_sources": 8,
                "assigned_water_sources": 123,
                "non_assigned_water_sources": 3,
            }
        """
        water_sources = self.get_all_water_sources()
        assigned_dict = self.check_if_water_sources_are_assigned(water_sources=water_sources)
        stats_dict = {
            "total_water_sources": len(water_sources),
            "assigned_water_sources": len(assigned_dict["assigned"]),
            "non_assigned_water_sources": len(assigned_dict["non-assigned"]),
        }

        return stats_dict

    def send_event(self, topic, key, payload):
        """
        Send event to the broker .

        @param topic: topic to send on .
        @param key: key of the event .
        @param payload: the payload of the event .
        @return:
        """
        return self.broker_repo.send_event(topic=topic, key=key, payload=payload)

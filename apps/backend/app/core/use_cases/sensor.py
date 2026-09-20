import logging

import common.constants as global_constants
from core.entities.sensor import Sensor as SensorEntity
from core.use_cases.base import BaseUseCase

logger = logging.getLogger(__name__)


class SensorUseCase(BaseUseCase):
    IDENTIFIER = "serial_number"
    ENTITY = SensorEntity

    def __init__(self, repo, zone_repo=None, zone_sensors_repo=None, water_source_repo=None, water_switcher_repo=None):
        """
        Initialize the use case with a repository.

        @param repo: Repository instance handling data operations.
        """
        super().__init__(repo)
        self.zone_repo = zone_repo
        self.zone_sensors_repo = zone_sensors_repo
        self.water_source_repo = water_source_repo
        self.water_switcher_repo = water_switcher_repo

    def get_sensor_type_by_serial_number(self, serial_number: str):
        """
         get the sensor type by serial number
        @param serial_number: str that represents the serial number of the sensor
        @return: str : the type of the sensor
        """
        filter_by = [
            {"attribute": "serial_number", "value": serial_number, "condition": "eq"},
        ]
        sensor_entities = super().filter(filters=filter_by)

        return sensor_entities[0].type

    def filter_by_zone_name(self, zone_name, order_by, order_direction):
        """
        Filter the sensor by Zone Name
        Logic:
            1- Get all the zone's sensors.
            2- Extract only the serial numbers from 1) result
            3- If the zone does not have any sensors just return []
            4- Else Create a new filters for the serial_number:
                {
                    'attribute': 'serial_number',
                    'value': zone_sensors_serial_numbers,
                    'condition': 'in'
                }
            5- Append the new filters  (serial numbers) to the other filters
            6- Call the self.filter with the updated filter
        @param zone_name: Str zone name
        @param order_by:
        @param order_direction:
        @return:
        """
        from core.use_cases.zone import ZoneUseCase  # to resolve the circular import

        filters = []
        # 1- Get the Zone sensor serial numbers
        zone_use_case = ZoneUseCase(
            repo=self.zone_repo, zone_sensors_repo=self.zone_sensors_repo, sensor_repo=self.repo
        )
        zone_sensors_data = zone_use_case.get_zone_sensors(zone_name=zone_name)
        zone_sensors_serial_numbers = list(zone_sensors_data.values())
        if not zone_sensors_serial_numbers:
            # No sensors for this zone
            return []
        serial_number_filter = {"attribute": "serial_number", "value": zone_sensors_serial_numbers, "condition": "in"}
        filters.append(serial_number_filter)
        return self.repo.filter(filters, order_by, order_direction)

    def check_if_sensor_is_assigned(self, sensor_serial_number: str, sensor_type: str):
        """
        This method check if the sensor is assigned or not :
        1- check the sensor type :  - if source_sensor check if it's assigned to a water source
                                    - elif switcher_sensor check if it's assigned to a water switcher
                                    - else it will be a zone sensor so check if it's assigned to a zone
        2- if it is assigned return the sensor assigned to zone name , serial number of water switcher or water source
        3- else return false
        @param sensor_serial_number: a unique serial number
        @param sensor_type:  the sensor type
        @return: str : the sensor assigned to zone name , serial number of water switcher or water source
        """
        from core.use_cases.water_source import WaterSourceUseCase  # to resolve the circular import
        from core.use_cases.water_switcher import WaterSwitcherUseCase  # to resolve the circular import
        from core.use_cases.zone_sensors import ZoneSensorsUseCase  # to resolve the circular import

        assigned = None
        filter_by = [
            {"attribute": "sensor_serial_number", "value": sensor_serial_number, "condition": "eq"},
        ]
        if sensor_type == global_constants.SOURCE_SENSOR:
            water_source_use_case = WaterSourceUseCase(
                repo=self.water_source_repo, sensor_repo=self.repo, sensor_record_repo=None
            )
            sensors = water_source_use_case.filter(filters=filter_by)
            if sensors:
                assigned = sensors[0].serial_number
        elif sensor_type == global_constants.SWITCHER_SENSOR:
            switcher_source_use_case = WaterSwitcherUseCase(repo=self.water_switcher_repo, sensor_repo=self.repo)
            sensors = switcher_source_use_case.filter(filters=filter_by)
            if sensors:
                assigned = sensors[0].serial_number
        elif sensor_type in global_constants.ZONE_SENSORS:
            zone_sensors_use_case = ZoneSensorsUseCase(repo=self.zone_sensors_repo, sensor_repo=self.repo)
            sensors = zone_sensors_use_case.filter(filters=filter_by)
            if sensors:
                assigned = sensors[0].zone_name
        else:
            logger.debug("Verify sensor type and sensor serial number are correct")

        return assigned

    def check_if_sensors_are_assigned(self, sensors: list):
        """
        This method checks if the sensors are assigned or not :
        logic:
        1- loop over all sensors and check if each sensor is assigned
        2 - if assigned add it to, assigned values
        3-  else add to non-assigned values
        4- return the dict
        @param sensors: list of sensors
        @return: a dict that has two keys assigned and non-assigned and their values are sensors
        """
        assigned_dict = {"assigned": [], "non-assigned": []}
        for sensor in sensors:
            serial_number = sensor.serial_number
            sensor_type = sensor.type
            if self.check_if_sensor_is_assigned(sensor_serial_number=serial_number, sensor_type=sensor_type):
                assigned_dict["assigned"].append(sensor)
            else:
                assigned_dict["non-assigned"].append(sensor)
        return assigned_dict

    def get_stats(self):
        """
        this method gets the sensors stats
        @return: dict
            {
                "total_sensors": 8,
                "assigned_sensors": 123,
                "non_assigned_sensors": 3,
            }
        """

        stats_dict = {}

        sensors = self.filter()
        assigned_dict = self.check_if_sensors_are_assigned(sensors=sensors)

        stats_dict["total_sensors"] = len(sensors)
        stats_dict["assigned_sensors"] = len(assigned_dict["assigned"])
        stats_dict["non_assigned_sensors"] = len(assigned_dict["non-assigned"])

        return stats_dict

    def _translate_filters(self, filters):
        """
        Replace a `zone_name` filter (not a Sensor column) by the `serial_number in (...)` filter
        of that zone's sensors, so the Filter DSL can be applied by the repository.
        """
        translated = []
        for item in filters or []:
            if item["attribute"] == "zone_name":
                from core.use_cases.zone import ZoneUseCase  # to resolve the circular import

                zone_use_case = ZoneUseCase(
                    repo=self.zone_repo, zone_sensors_repo=self.zone_sensors_repo, sensor_repo=self.repo
                )
                zone_sensors_data = zone_use_case.get_zone_sensors(zone_name=item["value"])
                translated.append(
                    {"attribute": "serial_number", "value": list(zone_sensors_data.values()), "condition": "in"}
                )
            else:
                translated.append(item)
        return translated

    def filter(self, filters=None, order_by="created_date", order_direction="asc"):
        """
              get all the sensors using the passed filter in the params
        Logic:
            1- Translate the FK filter (zone_name) into a serial_number filter
            2- Do the normal filter
        @param filters:
        @param order_by:
        @param order_direction:
        @return: list of sensor entities
        """
        return super().filter(self._translate_filters(filters), order_by, order_direction)

    def paginate(self, filters=None, order_by="created_date", order_direction="asc", limit=50, offset=0):
        return super().paginate(self._translate_filters(filters), order_by, order_direction, limit, offset)

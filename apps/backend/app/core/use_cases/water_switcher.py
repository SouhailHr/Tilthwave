import logging

from common import constants as global_constants
from core.entities.water_switcher import WaterSwitcher as WaterSwitcherEntity
from core.use_cases.base import BaseUseCase
from core.use_cases.exceptions import UseCaseException
from core.use_cases.sensor import SensorUseCase

logger = logging.getLogger(__name__)


class WaterSwitcherUseCase(BaseUseCase):
    ENTITY = WaterSwitcherEntity

    def __init__(self, repo, sensor_repo, broker_repo= None):
        """
        Initialize the use case with a repository.
        we are passing sensor_repo to handle validation
        of the sensor_type

        @param repo: Repository instance handling data operations.
        @param sensor_repo: Repository instance handling data operations for sensor entity
        @param broker_repo: Repository instance handling communication with broker
        """
        super().__init__(repo)
        self.broker_repo = broker_repo
        self.sensor_repo = sensor_repo

    def create(self, entity: ENTITY):
        """
        Create a water switcher entity using the repository.
        logic:
        1- get the sensor using serial_number
        2- verify sensor type == switcher_sensor
        3- raise exception if rule is not respected

        @param entity: Entity instance to be created.
        @return: The created entity.
        """
        filter_by = [{
            "attribute": "serial_number",
            "value": entity.sensor_serial_number,
            "condition": "eq"
        }]
        if entity.sensor_serial_number:
            sensor_use_case = SensorUseCase(repo=self.sensor_repo)
            sensor = sensor_use_case.filter(filters=filter_by)
            if sensor and sensor[0].type == global_constants.SWITCHER_SENSOR:
                return self.repo.create(entity)
            raise UseCaseException(class_name=self.__class__.__name__,
                                   message=f"water switcher can only have a sensor of type {global_constants.SWITCHER_SENSOR}")
        return self.repo.create(entity)

    def update(self, id: int, data: dict):
        """
            Update a water switcher entity using the repository.
        logic:
        1- Verify if the sensor_serial_number exists in the data if yes do 2 - 3 - 4
        1- get the sensor using switcher_sensor
        2- verify sensor type == switcher_sensor
        3- raise exception if rule is not respected

        @param id: ID of the entity to update.
        @param data: Dictionary of data to update.
        @return: The updated entity.
        """
        if data.get("sensor_serial_number"):
            sensor_serial_number = data["sensor_serial_number"]
            filter_by = [{
                "attribute": "serial_number",
                "value": sensor_serial_number,
                "condition": "eq"
            }]
            sensor_use_case = SensorUseCase(repo=self.sensor_repo)
            sensor = sensor_use_case.filter(filters=filter_by)
            if sensor and sensor[0].type == global_constants.SWITCHER_SENSOR:
                return self.repo.update(id, data)
            raise UseCaseException(class_name=self.__class__.__name__,
                                   message=f"water switcher can only have a sensor of type "
                                           f"{global_constants.SWITCHER_SENSOR}")

        return self.repo.update(id, data)

    def update_by_serial_number(self, serial_number, data: dict):
        """
        Update a water switcher by serial number.
        logic :
            If the water_switcher exist update it with the given data
            else remove the sensor serial number from the water switcher.
        @param serial_number: Serial number of the water switcher.
        @param data: Dictionary of data to update.
        @return: The updated entity.
        @raises UseCaseException: If an error occurs during the update process.
        """
        try:
            # Get the water switcher using the serial_number
            switcher_filter_by = [{
                "attribute": "serial_number",
                "value": serial_number,
                "condition": "eq"
            }]
            water_switchers = self.repo.filter(filters=switcher_filter_by)

            if water_switchers:
                # Update the water switcher with the provided data
                return self.repo.update(water_switchers[0].id, data)
            else:
                # Remove the sensor serial number from the water switcher
                sensor_serial_number = data["sensor_serial_number"]
                filter_by_sensor = [{
                    "attribute": "sensor_serial_number",
                    "value": sensor_serial_number,
                    "condition": "eq"
                }]
                water_switchers = self.filter(filters=filter_by_sensor)
                sensor_data = {"sensor_serial_number": None}
                if water_switchers:
                    return self.repo.update(water_switchers[0].id, sensor_data)
        except Exception as e:
            logger.debug(str(e))
            raise UseCaseException(class_name=self.__class__.__name__, message=str(e))

    def update_by_sensor_serial_number(self, sensor_serial_number, data: dict):
        """
        Update a water switcher by sensor serial number.
        logic :
            If the water_switcher exist update it with the given data
        @param sensor_serial_number: Serial number of the water switcher.
        @param data: Dictionary of data to update.
        @return: The updated entity.
        @raises UseCaseException: If an error occurs during the update process.
        """
        try:
            # Get the water switcher using the serial_number
            switcher_filter_by = [{
                "attribute": "sensor_serial_number",
                "value": sensor_serial_number,
                "condition": "eq"
            }]
            water_switchers = self.repo.filter(filters=switcher_filter_by)
            if water_switchers:
                # Update the water switcher with the provided data
                return self.repo.update(water_switchers[0].id, data)
            else:
                logger.info(f"no water switcher found assigned to the sensor {sensor_serial_number}")
        except Exception as e:
            logger.debug(str(e))
            raise UseCaseException(class_name=self.__class__.__name__, message=str(e))

    def get_all_water_switchers(self):
        """
        this method gets all water switchers
            @return: list of water switchers
        """
        water_switchers = self.filter()
        return water_switchers

    @staticmethod
    def check_if_water_switchers_are_assigned(water_switchers: list):
        """
        This method checks if the water_switchers are assigned or not :
        logic:
        1- loop over all water_sources and check if each water_switchers is assigned to a sensor
        2 - if assigned add it to, assigned values
        3-  else add to non-assigned values
        4- return the dict
        @param water_switchers: list of water_switchers
        @return: a dict that has two keys assigned and non-assigned and their values are sensors
        """
        assigned_dict = {"assigned": [], "non-assigned": []}
        for water_switcher in water_switchers:
            sensor = water_switcher.sensor_serial_number
            if sensor:
                assigned_dict["assigned"].append(water_switcher)
            else:
                assigned_dict["non-assigned"].append(water_switcher)
        return assigned_dict

    def get_stats(self):
        """
        this method gets the water sources stats
        @return: dict
            {
                "total_water_switchers": 8,
                "assigned_water_switchers": 123,
                "non_assigned_water_switchers": 3,
            }
        """
        water_switchers = self.get_all_water_switchers()
        assigned_dict = self.check_if_water_switchers_are_assigned(water_switchers=water_switchers)
        stats_dict = {
            "total_water_switchers": len(water_switchers),
            "assigned_water_switchers": len(assigned_dict["assigned"]),
            "non_assigned_water_switchers": len(assigned_dict["non-assigned"]),
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

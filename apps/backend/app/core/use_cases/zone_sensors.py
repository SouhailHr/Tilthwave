import logging

from adapters.zone_sensors import ZoneSensorsAdaptor
from common import constants as global_constants
from core.entities.zone_sensors import ZoneSensors
from core.use_cases.base import BaseUseCase
from core.use_cases.exceptions import UseCaseException
from core.use_cases.sensor import SensorUseCase

logger = logging.getLogger(__name__)


class ZoneSensorsUseCase(BaseUseCase):
    ENTITY = ZoneSensors

    def __init__(self, repo, sensor_repo):
        """
        Initialize the use case with a repository.
        we are passing sensor_repo to handle validation
        of the sensor_type

        @param repo: Repository instance handling data operations.
        @param sensor_repo: Repository instance handling data operations for sensor entity

        """
        super().__init__(repo)
        self.sensor_repo = sensor_repo

    def create(self, entity: ENTITY):
        """
        Create a zone sensors entity using the repository.
        logic:
        1- get the sensor using serial_number
        2- verify sensor type in [temperature_sensor,moisture_sensor,saturation_sensor]
        3- raise exception if rule is not respected

        @param entity: Entity instance to be created.
        @return: The created entity.
        """
        filter_by = [{
            "attribute": "serial_number",
            "value": entity.sensor_serial_number,
            "condition": "eq"
        }]
        sensor_use_case = SensorUseCase(repo=self.sensor_repo)
        sensor = sensor_use_case.filter(filters=filter_by)
        if sensor and sensor[0].type in global_constants.ZONE_SENSORS:
            return self.repo.create(entity)
        raise UseCaseException(class_name=self.__class__.__name__,
                               message=f"zone can only have a sensor of types {global_constants.ZONE_SENSORS}")

    def update(self, id: int, data: dict):
        """
            Update a zone sensors entity using the repository.
        logic:
        1- Verify if the sensor_serial_number exists in the data if yes do 2 - 3 - 4
        1- get the sensor using serial_number
        2- verify sensor type in [temperature_sensor,moisture_sensor,saturation_sensor]
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
            if sensor and sensor[0].type in global_constants.ZONE_SENSORS:
                return self.repo.update(id, data)
            raise UseCaseException(class_name=self.__class__.__name__,
                                   message=f"zone can only have a sensor of types {global_constants.ZONE_SENSORS}")

        return self.repo.update(id, data)

    def update_by_sensor_serial_number(self, sensor_serial_number, data: dict):
        """
         Update a zone sensors by sensor_serial_number
         logic :
         1- get the zone sensors entity using its sensor_serial_number
            1.1 - if zone sensors is not none get the zone name
                1.1.1 - if zone name is not none update the zone sensors by the new zone name and sensor serial number
                1.1.2 - if zone name is none delete the zone and sensors relation
            1.2- if the zone is none then create a new relation between the zone and the sensor
         2- if there is an exception return it
        @param sensor_serial_number: the serial number of the sensor
        @param data: the data that needs to be updated in the zone sensors
        @return:
        """
        try:
            # get the zone_sensors using the serial_number
            zone_sensors_filter_by = [{
                "attribute": "sensor_serial_number",
                "value": sensor_serial_number,
                "condition": "eq"
            }]
            zone_sensors = self.repo.filter(filters=zone_sensors_filter_by)
            if zone_sensors:
                # check if data has zone name
                if data.get("zone_name"):
                    # Update the relation
                    return self.repo.update(zone_sensors[0].id, data)
                # delete the relation
                return self.repo.delete(id=zone_sensors[0].id)
            # Create the relation
            zone_sensors_entity = ZoneSensorsAdaptor.dict_to_entity(data)
            return self.repo.create(zone_sensors_entity)
        except Exception as e:
            logger.debug(str(e))

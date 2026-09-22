import logging

from adapters.zone_sensors import ZoneSensorsAdaptor
from common import constants as global_constants
from core.entities.zone_sensors import ZoneSensors
from core.use_cases.base import BaseUseCase

logger = logging.getLogger(__name__)


class ZoneSensorsUseCase(BaseUseCase):
    ENTITY = ZoneSensors

    def __init__(self, repo, sensors):
        """
        @param repo: the zone<->sensor link repository
        @param sensors: SensorUseCase, for the attach rule (only zone sensor types may be linked)
        """
        super().__init__(repo)
        self.sensors = sensors

    def create(self, entity: ENTITY):
        self.sensors.require_type(entity.sensor_serial_number, tuple(global_constants.ZONE_SENSORS), owner="zone")
        return self.repo.create(entity)

    def update(self, id: int, data: dict):
        if data.get("sensor_serial_number"):
            self.sensors.require_type(data["sensor_serial_number"], tuple(global_constants.ZONE_SENSORS), owner="zone")
        return self.repo.update(id, data)

    def update_by_sensor_serial_number(self, sensor_serial_number, data: dict):
        """
        The link of `sensor_serial_number`: updated when `data` names a zone, deleted when it
        does not, created when there was none.
        """
        links = self.repo.filter(
            [{"attribute": "sensor_serial_number", "value": sensor_serial_number, "condition": "eq"}]
        )
        if links:
            if data.get("zone_name"):
                return self.repo.update(links[0].id, data)
            return self.repo.delete(id=links[0].id)
        return self.repo.create(ZoneSensorsAdaptor.dict_to_entity(data))

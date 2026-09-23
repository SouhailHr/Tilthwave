from common import constants as global_constants
from common.exceptions import NotFoundError
from core.entities.water_switcher import WaterSwitcher as WaterSwitcherEntity
from core.use_cases.actuator import ActuatorUseCase


class WaterSwitcherUseCase(ActuatorUseCase):
    ENTITY = WaterSwitcherEntity
    SENSOR_TYPE = global_constants.SWITCHER_SENSOR
    NOUN = "water switcher"

    def __init__(self, repo, sensors, water_sources, broker_repo=None):
        """
        @param water_sources: WaterSourceUseCase, tenant-scoped like every read, so the source a
               switcher is fed from must be one the caller can see. The FK alone checks existence,
               and the flow runner acts on the reference unscoped: without this an owner could
               point a switcher at another farm's pump and have it opened.
        """
        super().__init__(repo, sensors, broker_repo)
        self.water_sources = water_sources

    def _require_own_source(self, serial_number: str) -> None:
        found = self.water_sources.first([{"attribute": "serial_number", "value": serial_number, "condition": "eq"}])
        if found is None:
            raise NotFoundError("Water source not found")

    def create(self, entity):
        if entity.water_source_serial_number:
            self._require_own_source(entity.water_source_serial_number)
        return super().create(entity)

    def update(self, id: int, data: dict):
        if data.get("water_source_serial_number"):
            self._require_own_source(data["water_source_serial_number"])
        return super().update(id, data)

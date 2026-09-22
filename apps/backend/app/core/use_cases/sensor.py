import logging

import common.constants as global_constants
from core.entities.sensor import Sensor as SensorEntity
from core.use_cases.base import BaseUseCase
from core.use_cases.exceptions import UseCaseException

logger = logging.getLogger(__name__)


class SensorUseCase(BaseUseCase):
    ENTITY = SensorEntity

    def __init__(self, repo, zone_sensors_repo=None, water_source_repo=None, water_switcher_repo=None):
        """
        @param repo: the sensor repository
        @param zone_sensors_repo, water_source_repo, water_switcher_repo: the three link tables,
               read to answer what a sensor is attached to
        """
        super().__init__(repo)
        self.zone_sensors_repo = zone_sensors_repo
        self.water_source_repo = water_source_repo
        self.water_switcher_repo = water_switcher_repo

    def require_type(self, serial_number: str, allowed, owner: str):
        """
        The sensor `serial_number`, provided it exists (within the caller's farm) and is one of
        the `allowed` types; UseCaseException otherwise. The one rule every actuator and zone link
        enforces before attaching a sensor.
        @param owner: what is being attached to, for the message ("water source", "zone")
        """
        sensor = self.repo.first([{"attribute": "serial_number", "value": serial_number, "condition": "eq"}])
        if sensor is None or sensor.type not in allowed:
            raise UseCaseException(
                class_name=self.__class__.__name__,
                message=f"{owner} can only have a sensor of type {', '.join(allowed)}",
            )
        return sensor

    def assignments_for(self, sensors) -> dict:
        """
        What each sensor is attached to, for a whole page at once: {serial_number: zone name |
        switcher serial | source serial | None}. Three `IN` queries (one per link table) instead
        of one query per sensor.
        """
        sensors = list(sensors)
        by_type: dict = {}
        for sensor in sensors:
            by_type.setdefault(sensor.type, []).append(sensor.serial_number)
        assigned: dict = {}

        def lookup(repo, serials, label):
            if not serials:
                return
            rows = repo.filter([{"attribute": "sensor_serial_number", "value": serials, "condition": "in"}])
            for row in rows:
                assigned[row.sensor_serial_number] = getattr(row, label)

        lookup(self.water_source_repo, by_type.get(global_constants.SOURCE_SENSOR, []), "serial_number")
        lookup(self.water_switcher_repo, by_type.get(global_constants.SWITCHER_SENSOR, []), "serial_number")
        zone_serials = [sn for type_, sns in by_type.items() if type_ in global_constants.ZONE_SENSORS for sn in sns]
        lookup(self.zone_sensors_repo, zone_serials, "zone_name")
        return {sensor.serial_number: assigned.get(sensor.serial_number) for sensor in sensors}

    def _translate_filters(self, filters):
        """
        Replace a `zone_name` filter (not a Sensor column) by the `serial_number in (...)` filter
        of that zone's sensors, so the Filter DSL can be applied by the repository.
        """
        translated = []
        for item in filters or []:
            if item["attribute"] == "zone_name":
                links = self.zone_sensors_repo.filter(
                    [{"attribute": "zone_name", "value": item["value"], "condition": "eq"}]
                )
                serials = [link.sensor_serial_number for link in links]
                translated.append({"attribute": "serial_number", "value": serials, "condition": "in"})
            else:
                translated.append(item)
        return translated

    def filter(self, filters=None, order_by="created_date", order_direction="asc"):
        return super().filter(self._translate_filters(filters), order_by, order_direction)

    def paginate(self, filters=None, order_by="created_date", order_direction="asc", limit=50, offset=0):
        return super().paginate(self._translate_filters(filters), order_by, order_direction, limit, offset)

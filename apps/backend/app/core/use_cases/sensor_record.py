import logging

from core.entities.sensor_record import SensorRecord as SensorRecordEntity
from core.use_cases.base import BaseUseCase

logger = logging.getLogger(__name__)


class SensorRecordUseCase(BaseUseCase):
    ENTITY = SensorRecordEntity

    def get_latest_sensor_record(self, serial_number: str):
        """
        The most recent sensor record entity for a sensor (one row fetched), or None.

        @param serial_number: The serial number of the sensor to look up.
        @return: SensorRecord entity or None when the sensor has no records.
        """
        filter_by = [{"attribute": "sensor_serial_number", "value": serial_number, "condition": "eq"}]
        return self.first(filters=filter_by, order_by="created_date", order_direction="desc")

    def latest_per_sensor(self, serial_numbers, since=None) -> list:
        """The newest record of each sensor (at or after `since`), one query (see the repository)."""
        return self.repo.latest_per_sensor(serial_numbers, since=since)

    def monthly_consumption(self, serial_numbers, year: int, from_month: int = 1) -> dict[int, float]:
        """{month: total consumption} of `year` over the sensors, one query (see the repository)."""
        return self.repo.monthly_consumption(serial_numbers, year, from_month)

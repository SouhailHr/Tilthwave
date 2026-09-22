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

    def get_latest_senor_record_by_serial_number(self, serial_number: str):
        """
        Retrieve the latest sensor record data by the given serial number.

        @param serial_number: The serial number of the sensor to look up.
        @return: The latest sensor record data corresponding to the given serial number, or `None` if not found.
        """
        latest = self.get_latest_sensor_record(serial_number)
        return latest.data if latest else None

    def latest_per_sensor(self, serial_numbers) -> list:
        """The newest record of each sensor, one query for all of them (see the repository)."""
        return self.repo.latest_per_sensor(serial_numbers)

    def monthly_consumption(self, serial_numbers, year: int) -> dict[int, float]:
        """{month: total consumption} of `year` over the sensors, one query (see the repository)."""
        return self.repo.monthly_consumption(serial_numbers, year)

    def get_get_sensor_records(self, serial_number: str, limit: int | None = None):
        """
            Retrieve sensor records by the given serial number, newest first.
        @param serial_number: The serial number of the sensor to look up.
        @param limit: at most this many rows, fetched as such; None means every record
        @return: list of SensorRecord entities
        """
        filter_by = [
            {"attribute": "sensor_serial_number", "value": serial_number, "condition": "eq"},
        ]
        return self.repo.filter(filters=filter_by, order_by="created_date", order_direction="desc", limit=limit)

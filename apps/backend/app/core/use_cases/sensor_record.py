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

    def get_get_sensor_records(self, serial_number: str):
        """
            Retrieve all sensor record data by the given serial number.
        @param serial_number: The serial number of the sensor to look up.
        @return: dict of data
        """
        filter_by = [
            {"attribute": "sensor_serial_number", "value": serial_number, "condition": "eq"},
        ]
        sensor_records = self.repo.filter(filters=filter_by, order_by="created_date", order_direction="desc")
        return sensor_records

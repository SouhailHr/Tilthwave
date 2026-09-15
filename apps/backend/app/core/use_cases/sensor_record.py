from core.entities.sensor_record import SensorRecord as SensorRecordEntity
from core.use_cases.base import BaseUseCase
from core.use_cases.exceptions import UseCaseException
import logging

logger = logging.getLogger(__name__)


class SensorRecordUseCase(BaseUseCase):
    ENTITY = SensorRecordEntity

    def get_latest_senor_record_by_serial_number(self, serial_number: str):
        """
        Retrieve the latest sensor record data by the given serial number.
        logic :
            1- get the sensor records
            2- Compare the sensor records by updated_date and save latest always
            3- return the latest sensor record data
            4- raise an exception if the sensor has no records or doesn't exist

        @param serial_number: The serial number of the sensor to look up.
        @return: The latest sensor record data corresponding to the given serial number, or `None` if not found.
        """
        filter_by = [{
            "attribute": "sensor_serial_number",
            "value": serial_number,
            "condition": "eq"
        }]
        sensor_records = self.repo.filter(filters=filter_by, order_by="created_date", order_direction="desc")
        if sensor_records:
            latest = sensor_records[0]
            return latest.data

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

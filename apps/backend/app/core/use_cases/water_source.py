import logging

from common import constants as global_constants
from common.dates import command_timestamp
from config.settings import settings
from core.entities.water_source import WaterSource as WaterSourceEntity
from core.use_cases.actuator import ActuatorUseCase

logger = logging.getLogger(__name__)


class WaterSourceUseCase(ActuatorUseCase):
    ENTITY = WaterSourceEntity
    SENSOR_TYPE = global_constants.SOURCE_SENSOR
    NOUN = "water source"

    def close_all_water_sources(self):
        """
        Close every water source that is currently On.
        @raises BrokerError: if a close command could not be delivered (the caller decides
                             whether to retry; the source may still be open)
        """
        for water_source in self.filter():
            if water_source.sensor_serial_number and water_source.status == global_constants.STATUS_ON:
                self.send_event(
                    topic=settings.STREAMER.WATER_CONTROL_TOPIC,
                    key="water_control_data",
                    payload=self.build_status_command(water_source, global_constants.STATUS_OFF),
                )

    @staticmethod
    def build_status_command(water_source, status: str) -> dict:
        """Command payload asking the water source's actuator to switch to `status`."""
        return {
            "sensor_serial_number": water_source.sensor_serial_number,
            "data": {
                "type": "source",
                "status": status,  # operational status
                "timestamp": command_timestamp(),
            },
        }

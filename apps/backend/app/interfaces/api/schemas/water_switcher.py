from typing import Optional

from pydantic import BaseModel, Field
import common.constants as global_constants


class WaterSwitcherCreate(BaseModel):
    """
    Schema for creating a new water Switcher. Includes validation and serialization logic.
    """
    water_source_serial_number: str = Field(
        description="The serial_number of the water_source associated with this water switcher.")
    sensor_serial_number: Optional[str] = None
    Field(
        description="The serial_number of the sensor associated with this water source.")
    status: str = Field(pattern=global_constants.WATER_SWITCHER_STATUS)
    zone_name: str = Field(description="The name of the zone that the switcher belongs to.", max_length=100)
    serial_number: str = Field(description="Unique serial number of the Water switcher")

    class Config:
        json_schema_extra = {
            "example": {
                "sensor_serial_number": "WSWSN123457",
                "water_source_serial_number": "WSDEEP00123",
                "zone_name": "Zone 1",
                "status": "On",
                "serial_number": "WS00123"
            }
        }

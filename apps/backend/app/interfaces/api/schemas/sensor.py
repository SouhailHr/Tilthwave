from typing import Optional

from pydantic import BaseModel, Field
from common import constants as global_constants


class SensorCreate(BaseModel):
    """
    Schema for creating a new sensor, includes validation and serialization logic.
    """
    type: str = Field(pattern=global_constants.SENSOR_TYPES)
    is_active: Optional[bool] = True
    serial_number: str = Field(description="Unique serial number of the sensor")
    assigned_to_type: Optional[str] = None
    zone_name: Optional[str] = None
    water_switcher: Optional[str] = None
    water_source: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "type": "temperature_sensor",
                "is_active": True,
                "serial_number": "SENTEMP00123"
            }
        }

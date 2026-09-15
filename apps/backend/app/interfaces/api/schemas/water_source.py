from typing import Optional

from pydantic import BaseModel, Field
import common.constants as global_constants


class WaterSourceCreate(BaseModel):
    """
    Schema for creating a new water source. Includes validation and serialization logic.
    """
    farm_name: str = Field(description="The name of the farm that the water source is associated with.")
    sensor_serial_number: Optional[str] = None
    Field(description="The serial_number of the sensor associated with this water source.")
    type: str = Field(description="The type of water source.", max_length=50)
    water_pressure: float = Field(description="Pressure of water at the source in PSI.", gt=0)
    water_volume: float = Field(description="Volume of water available at the source in cubic meters.", gt=0)
    status: str = Field(pattern=global_constants.WATER_SOURCE_STATUS)
    serial_number: str = Field(description="Unique serial number of the Water source")

    class Config:
        json_schema_extra = {
            "example": {
                "farm_name": "Sunny Farms",
                "sensor_serial_number": "WSOSN123456",
                "type": "deep groundwater",
                "water_pressure": 15.5,
                "water_volume": 1000.0,
                "status": global_constants.STATUS_ON,
                "serial_number": "WSDEEP00123"
            }
        }

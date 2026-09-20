from pydantic import BaseModel, ConfigDict, Field

import common.constants as global_constants
from interfaces.api.schemas.base import IDENTIFIER_DOC


class WaterSourceCreate(BaseModel):
    """
    Schema for creating a new water source. Includes validation and serialization logic.
    """

    farm_name: str = Field(description="The name of the farm that the water source is associated with.")
    sensor_serial_number: str | None = None
    Field(description="The serial_number of the sensor associated with this water source.")
    type: str = Field(description="The type of water source.", max_length=50)
    water_pressure: float = Field(description="Pressure of water at the source in PSI.", gt=0)
    water_volume: float = Field(description="Volume of water available at the source in cubic meters.", gt=0)
    status: str = Field(pattern=global_constants.WATER_SOURCE_STATUS)
    serial_number: str = Field(description="Unique serial number of the Water source")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "farm_name": "Sunny Farms",
                "sensor_serial_number": "WSOSN123456",
                "type": "deep groundwater",
                "water_pressure": 15.5,
                "water_volume": 1000.0,
                "status": global_constants.STATUS_ON,
                "serial_number": "WSDEEP00123",
            }
        }
    )


class WaterSourceUpdate(BaseModel):
    """
    Schema for a partial water source update (PATCH); unknown fields are rejected.
    `serial_number` and `farm_name` are identifiers and are not updatable here.
    """

    model_config = ConfigDict(extra="forbid")

    serial_number: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)
    farm_name: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)

    sensor_serial_number: str | None = Field(
        default=None, description="The serial_number of the sensor of this water source."
    )
    type: str | None = Field(default=None, description="The type of water source.", max_length=50)
    water_pressure: float | None = Field(default=None, gt=0, description="Pressure of water at the source in PSI.")
    water_volume: float | None = Field(default=None, gt=0, description="Volume of water available in cubic meters.")
    status: str | None = Field(default=None, pattern=global_constants.WATER_SOURCE_STATUS)

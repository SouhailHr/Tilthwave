from pydantic import BaseModel, ConfigDict, Field

from common import constants as global_constants
from interfaces.api.schemas.base import IDENTIFIER_DOC


class SensorCreate(BaseModel):
    """
    Schema for creating a new sensor, includes validation and serialization logic.
    """

    type: str = Field(pattern=global_constants.SENSOR_TYPES)
    is_active: bool | None = True
    serial_number: str = Field(description="Unique serial number of the sensor")
    assigned_to_type: str = Field(
        pattern="^(zone|water_switcher|water_source)$", description="Which relation to create alongside the sensor."
    )
    zone_name: str | None = None
    water_switcher: str | None = None
    water_source: str | None = None

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"type": "temperature_sensor", "is_active": True, "serial_number": "SENTEMP00123"}
        },
    )


class SensorUpdate(BaseModel):
    """
    Schema for a partial sensor update (PATCH); unknown fields are rejected.
    `assigned_to_type` selects which relation (zone / water_switcher / water_source) is updated
    alongside the sensor, mirroring SensorCreate.
    """

    model_config = ConfigDict(extra="forbid")

    farm_name: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)
    type: str | None = Field(default=None, pattern=global_constants.SENSOR_TYPES)
    is_active: bool | None = None
    serial_number: str | None = Field(default=None, description="Unique serial number of the sensor")
    assigned_to_type: str | None = Field(default=None, pattern="^(zone|water_switcher|water_source)$")
    zone_name: str | None = None
    water_switcher: str | None = None
    water_source: str | None = None

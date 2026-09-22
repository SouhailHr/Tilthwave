from pydantic import BaseModel, ConfigDict, Field

import common.constants as global_constants
from interfaces.api.schemas.base import IDENTIFIER_DOC


class WaterSwitcherCreate(BaseModel):
    """
    Schema for creating a new water Switcher. Includes validation and serialization logic.
    """

    water_source_serial_number: str = Field(
        description="The serial_number of the water_source associated with this water switcher."
    )
    sensor_serial_number: str | None = None
    Field(description="The serial_number of the sensor associated with this water source.")
    status: str = Field(pattern=global_constants.WATER_SWITCHER_STATUS)
    zone_name: str = Field(description="The name of the zone that the switcher belongs to.", max_length=100)
    serial_number: str = Field(description="Unique serial number of the Water switcher")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "sensor_serial_number": "WSWSN123457",
                "water_source_serial_number": "WSDEEP00123",
                "zone_name": "Zone 1",
                "status": "On",
                "serial_number": "WS00123",
            }
        },
    )


class WaterSwitcherUpdate(BaseModel):
    """
    Schema for a partial water switcher update (PATCH); unknown fields are rejected.
    `serial_number` is an identifier and is not updatable here.
    """

    model_config = ConfigDict(extra="forbid")

    serial_number: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)

    water_source_serial_number: str | None = Field(
        default=None, description="The serial_number of the feeding water source."
    )
    sensor_serial_number: str | None = Field(default=None, description="The serial_number of the switcher's sensor.")
    status: str | None = Field(default=None, pattern=global_constants.WATER_SWITCHER_STATUS)
    zone_name: str | None = Field(
        default=None, description="The name of the zone the switcher belongs to.", max_length=100
    )

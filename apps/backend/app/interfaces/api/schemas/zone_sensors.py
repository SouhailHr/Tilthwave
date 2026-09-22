from pydantic import BaseModel, ConfigDict, Field


class ZoneSensorCreate(BaseModel):
    """
    Schema for creating a new zone sensor association, includes validation and serialization logic.
    """

    sensor_serial_number: str = Field(
        description="The serial_number of the sensor, must be A valid existing sensor serial number."
    )
    zone_name: str = Field(description="The Zone name ,is required")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "sensor_serial_number": "TSN123456",
                "zone_name": "Zone 1",
            }
        },
    )


class ZoneSensorUpdate(BaseModel):
    """
    Schema for a partial zone-sensor link update (PATCH); unknown fields are rejected.
    """

    model_config = ConfigDict(extra="forbid")

    sensor_serial_number: str | None = Field(default=None, description="A valid existing sensor serial number.")
    zone_name: str | None = Field(default=None, description="The Zone name.")

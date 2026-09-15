from pydantic import BaseModel, Field


class ZoneSensorCreate(BaseModel):
    """
    Schema for creating a new zone sensor association, includes validation and serialization logic.
    """
    sensor_serial_number: str = Field(
        description="The serial_number of the sensor, must be A valid existing sensor serial number.")
    zone_name: str = Field(description="The Zone name ,is required")

    class Config:
        json_schema_extra = {
            "example": {
                "sensor_serial_number": "TSN123456",
                "zone_name": "Zone 1",
            }
        }

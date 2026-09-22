from pydantic import BaseModel, ConfigDict, Field


class SensorRecordCreate(BaseModel):
    """
    Schema for creating a new sensor record, includes validation and serialization logic.
    """

    sensor_serial_number: str = Field(description="The serial_number of the sensor associated with this record.")
    data: dict = Field(description="JSON format containing the sensor data collected.")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "sensor_serial_number": "SN456488",
                "data": {"temperature": 22.5, "timestamp": "2024-05-08T14:36:09.118088"},
            }
        },
    )

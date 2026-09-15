from typing import Optional
from pydantic import BaseModel, Field


class ZoneCreate(BaseModel):
    """
    Schema for creating a new zone, includes validation and serialization logic.
    """
    farm_name: str = Field(description="The name of the farm this zone belongs to.", max_length=100)
    zone_name: str = Field(description="The unique name or description of the zone.", max_length=100)
    size: int = Field(gt=0, description="The size of the zone in square meters.")
    location: Optional[dict] = Field(default=None,
                                     description="Geographical details of the zone stored"
                                                 " in JSON format such as coordinates.")
    soil_type: str = Field(description="Type of soil within the zone.", max_length=50)

    # Triggers for the zone irrigation

    moisture_trigger_start: int = Field(description="Moisture trigger start value.")
    moisture_trigger_stop: int = Field(description="Moisture trigger stop value.")
    saturation_trigger_start: int = Field(description="Saturation trigger start value.")
    saturation_trigger_stop: int = Field(description="Saturation trigger stop value.")

    class Config:
        json_schema_extra = {
            "example": {
                "farm_name": "Sunny Farms",
                "zone_name": "Zone 1",
                "size": 1500,
                "location": {
                    "latitude": 39.7817,
                    "longitude": -89.6501
                },
                "soil_type": "Loamy",
                "moisture_trigger_start": 50,
                "moisture_trigger_stop": 80,
                "saturation_trigger_start": 60,
                "saturation_trigger_stop": 90
            }
        }

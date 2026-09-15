import datetime
from datetime import date

from pydantic import BaseModel, Field


class TreeCreate(BaseModel):
    """
    Schema for creating a new tree, includes validation and serialization logic.
    """
    zone_name: str = Field(description="The name of the zone where the tree is planted.")
    variety: str = Field(description="The species or variety of the tree.")
    planting_date: str = Field(description="The date when the tree was planted.")
    height: float = Field(description="Current height of the tree in meters.")
    width_diameter: float = Field(description="Width or canopy diameter of the tree in meters.")
    trunk_diameter: float = Field(description="Diameter of the tree trunk in centimeters.")
    serial_number: str = Field(description="Unique serial number of the tree")

    class Config:
        json_schema_extra = {
            "example": {
                "zone_name": "Zone 1",
                "variety": "Maple",
                "planting_date": "2024-01-01",
                "height": 5.5,
                "width_diameter": 2.0,
                "trunk_diameter": 0.3,
                "serial_number": "OLIVE00123"
            }
        }

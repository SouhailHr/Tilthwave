from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from interfaces.api.schemas.base import IDENTIFIER_DOC


class TreeCreate(BaseModel):
    """
    Schema for creating a new tree, includes validation and serialization logic.
    """

    zone_name: str = Field(description="The name of the zone where the tree is planted.")
    variety: str = Field(description="The species or variety of the tree.")
    planting_date: date = Field(description="The date when the tree was planted (YYYY-MM-DD).")
    height: float = Field(description="Current height of the tree in meters.")
    width_diameter: float = Field(description="Width or canopy diameter of the tree in meters.")
    trunk_diameter: float = Field(description="Diameter of the tree trunk in centimeters.")
    serial_number: str = Field(description="Unique serial number of the tree")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "zone_name": "Zone 1",
                "variety": "Maple",
                "planting_date": "2024-01-01",
                "height": 5.5,
                "width_diameter": 2.0,
                "trunk_diameter": 0.3,
                "serial_number": "OLIVE00123",
            }
        },
    )


class TreeUpdate(BaseModel):
    """
    Schema for a partial tree update (PATCH); unknown fields are rejected.
    """

    model_config = ConfigDict(extra="forbid")

    serial_number: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)

    zone_name: str | None = Field(default=None, description="The name of the zone where the tree is planted.")
    variety: str | None = Field(default=None, description="The species or variety of the tree.")
    planting_date: date | None = Field(default=None, description="The date when the tree was planted (YYYY-MM-DD).")
    height: float | None = Field(default=None, gt=0, description="Current height of the tree in meters.")
    width_diameter: float | None = Field(default=None, gt=0, description="Canopy diameter of the tree in meters.")
    trunk_diameter: float | None = Field(default=None, gt=0, description="Diameter of the trunk in centimeters.")

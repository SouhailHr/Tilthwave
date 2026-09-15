from pydantic import BaseModel, ConfigDict, Field

from interfaces.api.schemas.base import IDENTIFIER_DOC


class FarmCreate(BaseModel):
    """
    Schema for creating a new farm, includes validation and serialization logic.
    """

    farm_name: str = Field(..., description="The unique name of the farm.", max_length=100)
    address: str = Field(..., description="The physical address of the farm.", max_length=255)
    location: dict | None = Field(
        default=None, description="A JSON object storing detailed location data such as coordinates."
    )
    size: float = Field(..., gt=0, description="The total area of the farm in acres.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "farm_name": "Sunny Farms",
                "address": "100 Farmer Way, Springfield, IL",
                "location": {"latitude": 39.7817, "longitude": -89.6501},
                "size": 120.0,
            }
        }
    )


class FarmUpdate(BaseModel):
    """
    Schema for a partial farm update (PATCH); unknown fields are rejected.
    """

    model_config = ConfigDict(extra="forbid")

    farm_name: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)

    address: str | None = Field(default=None, description="The physical address of the farm.", max_length=255)
    location: dict | None = Field(
        default=None, description="A JSON object storing detailed location data such as coordinates."
    )
    size: float | None = Field(default=None, gt=0, description="The total area of the farm in acres.")

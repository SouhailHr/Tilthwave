from pydantic import BaseModel, ConfigDict, Field, model_validator

from interfaces.api.schemas.base import IDENTIFIER_DOC

TRIGGER_MIN = 0
TRIGGER_MAX = 100


def validate_triggers(values: dict) -> None:
    """
    Cross-field rule shared by create and update: for moisture and saturation, the stop
    trigger must be strictly above the start trigger, otherwise irrigation would start and
    stop on the same reading. Only checked for the pairs present (partial updates).
    """
    for kind in ("moisture", "saturation"):
        start, stop = values.get(f"{kind}_trigger_start"), values.get(f"{kind}_trigger_stop")
        if start is not None and stop is not None and stop <= start:
            raise ValueError(f"{kind}_trigger_stop must be greater than {kind}_trigger_start")


class ZoneCreate(BaseModel):
    """
    Schema for creating a new zone, includes validation and serialization logic.
    """

    farm_name: str = Field(description="The name of the farm this zone belongs to.", max_length=100)
    zone_name: str = Field(description="The unique name or description of the zone.", max_length=100)
    size: int = Field(gt=0, description="The size of the zone in square meters.")
    location: dict | None = Field(
        default=None, description="Geographical details of the zone stored in JSON format such as coordinates."
    )
    soil_type: str = Field(description="Type of soil within the zone.", max_length=50)

    # Triggers for the zone irrigation

    moisture_trigger_start: int = Field(ge=TRIGGER_MIN, le=TRIGGER_MAX, description="Moisture trigger start value.")
    moisture_trigger_stop: int = Field(ge=TRIGGER_MIN, le=TRIGGER_MAX, description="Moisture trigger stop value.")
    saturation_trigger_start: int = Field(ge=TRIGGER_MIN, le=TRIGGER_MAX, description="Saturation trigger start value.")
    saturation_trigger_stop: int = Field(ge=TRIGGER_MIN, le=TRIGGER_MAX, description="Saturation trigger stop value.")

    @model_validator(mode="after")
    def triggers_are_consistent(self):
        validate_triggers(self.model_dump())
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "farm_name": "Sunny Farms",
                "zone_name": "Zone 1",
                "size": 1500,
                "location": {"latitude": 39.7817, "longitude": -89.6501},
                "soil_type": "Loamy",
                "moisture_trigger_start": 50,
                "moisture_trigger_stop": 80,
                "saturation_trigger_start": 60,
                "saturation_trigger_stop": 90,
            }
        }
    )


class ZoneUpdate(BaseModel):
    """
    Schema for a partial zone update (PATCH); unknown fields are rejected.
    `farm_name` and `zone_name` are identifiers other rows reference and are not updatable here.
    """

    model_config = ConfigDict(extra="forbid")

    farm_name: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)
    zone_name: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)

    size: int | None = Field(default=None, gt=0, description="The size of the zone in square meters.")
    location: dict | None = Field(default=None, description="Geographical details of the zone.")
    soil_type: str | None = Field(default=None, description="Type of soil within the zone.", max_length=50)
    moisture_trigger_start: int | None = Field(default=None, ge=TRIGGER_MIN, le=TRIGGER_MAX)
    moisture_trigger_stop: int | None = Field(default=None, ge=TRIGGER_MIN, le=TRIGGER_MAX)
    saturation_trigger_start: int | None = Field(default=None, ge=TRIGGER_MIN, le=TRIGGER_MAX)
    saturation_trigger_stop: int | None = Field(default=None, ge=TRIGGER_MIN, le=TRIGGER_MAX)

    @model_validator(mode="after")
    def triggers_are_consistent(self):
        validate_triggers(self.model_dump(exclude_unset=True))
        return self

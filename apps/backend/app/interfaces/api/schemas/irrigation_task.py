from pydantic import BaseModel, ConfigDict, Field, constr

import common.constants as global_constants
from interfaces.api.schemas.base import IDENTIFIER_DOC


class IrrigationTaskCreate(BaseModel):
    """
    Schema for creating a new irrigation task, includes validation and serialization logic.
    """

    zone_name: str = Field(description="The name of the zone where the task is applied.")
    status: constr(pattern=global_constants.IRRIGATION_TASK_STATUS) = Field(
        description="Current status of the task (e.g., pending, in progress, completed, canceled)."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "zone_name": "Zone 1",
                "status": "pending",
            }
        }
    )


class IrrigationTaskUpdate(BaseModel):
    """
    Schema for a partial irrigation task update (PATCH); unknown fields are rejected.
    """

    model_config = ConfigDict(extra="forbid")

    zone_name: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)

    status: constr(pattern=global_constants.IRRIGATION_TASK_STATUS) | None = Field(
        default=None, description="Current status of the task (pending, in progress, completed, canceled)."
    )
    duration: int | None = Field(default=None, ge=0, description="Duration of the irrigation in minutes.")

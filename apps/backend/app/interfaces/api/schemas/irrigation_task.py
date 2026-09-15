from pydantic import BaseModel, Field, constr
import common.constants as global_constants


class IrrigationTaskCreate(BaseModel):
    """
    Schema for creating a new irrigation task, includes validation and serialization logic.
    """
    zone_name: str = Field(description="The name of the zone where the task is applied.")
    status: constr(pattern=global_constants.IRRIGATION_TASK_STATUS) = Field(
        description="Current status of the task (e.g., pending, in progress, completed, canceled).")

    class Config:
        json_schema_extra = {
            "example": {
                "zone_name": "Zone 1",
                "status": "pending",
            }
        }

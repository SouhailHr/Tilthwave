import dataclasses

from core.entities.base import BaseEntity


@dataclasses.dataclass
class IrrigationTask(BaseEntity):
    """
        IrrigationTask is an entity that represents an irrigation_task, extending BaseEntity.
    """

    zone_name: str
    status: str
    duration: int = None
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = "Flow Runner"

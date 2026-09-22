import dataclasses

from core.entities.base import BaseEntity


@dataclasses.dataclass
class Sensor(BaseEntity):
    """
    Sensor is an entity that represents a sensor, extending BaseEntity.
    """

    type: str
    serial_number: str
    is_active: bool = True
    farm_name: str = None
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

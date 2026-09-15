import dataclasses

from core.entities.base import BaseEntity


@dataclasses.dataclass
class Tree(BaseEntity):
    """
     Tree is an entity that represents a tree, extending BaseEntity.
    """
    zone_name: str
    variety: str
    height: float
    width_diameter: float
    trunk_diameter: float
    planting_date: str
    serial_number: str
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

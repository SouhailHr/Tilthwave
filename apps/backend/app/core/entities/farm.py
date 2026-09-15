import dataclasses
from typing import Optional, Dict

from core.entities.base import BaseEntity


@dataclasses.dataclass
class Farm(BaseEntity):
    """
    Farm is an entity that represents a farm, extending BaseEntity.
    Includes farm name, address, location data, size, and list of managers.
    """
    farm_name: str
    address: str
    location: Optional[Dict]  # Assuming location is a dictionary storing JSON-like data
    size: float
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

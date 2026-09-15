import dataclasses

from core.entities.base import BaseEntity


@dataclasses.dataclass
class Zone(BaseEntity):
    """
    Zone is an entity that represents a zone, extending BaseEntity.
    """

    farm_name: str
    zone_name: str
    size: int
    location: dict
    soil_type: str
    moisture_trigger_start: int
    moisture_trigger_stop: int
    saturation_trigger_start: int
    saturation_trigger_stop: int
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

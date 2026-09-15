import dataclasses

from core.entities.base import BaseEntity


@dataclasses.dataclass
class WaterSwitcher(BaseEntity):
    """
     WaterSwitcher is an entity that represents a water_switcher, extending BaseEntity.
    """
    status: str
    water_source_serial_number: str
    zone_name: str
    serial_number: str
    sensor_serial_number: str = None
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

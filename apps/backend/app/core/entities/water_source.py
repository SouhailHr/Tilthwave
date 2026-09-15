import dataclasses

from core.entities.base import BaseEntity


@dataclasses.dataclass
class WaterSource(BaseEntity):
    """
     WaterSource is an entity that represents a water_source, extending BaseEntity.
    """
    farm_name: str
    type: str
    water_pressure: float
    water_volume: float
    status: str
    serial_number: str
    sensor_serial_number: str = None
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

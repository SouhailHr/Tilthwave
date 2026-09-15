import dataclasses

from core.entities.base import BaseEntity


@dataclasses.dataclass
class ZoneSensors(BaseEntity):
    """
    ZoneSensors is an entity that represents the sensors of each zone, extending BaseEntity.
    """

    sensor_serial_number: str
    zone_name: str
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

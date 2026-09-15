import dataclasses

from core.entities.base import BaseEntity


@dataclasses.dataclass
class SensorRecord(BaseEntity):
    """
     Sensor is an entity that represents a sensor, extending BaseEntity.
    """
    sensor_serial_number: str
    data: dict
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

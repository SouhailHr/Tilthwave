from adapters.zone_sensors import ZoneSensorsAdaptor
from core.entities.zone_sensors import ZoneSensors as ZoneSensorsEntity
from infrastructure.database.tables.zone_sensors import ZoneSensors
from infrastructure.repositories.base import BaseDBRepo


class ZoneSensorsDBRepository(BaseDBRepo):
    """
    ZoneSensorsDBRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """
    MODEL = ZoneSensors
    ENTITY = ZoneSensorsEntity
    ADAPTOR = ZoneSensorsAdaptor
    TENANT_SCOPE = ("via_zone",)

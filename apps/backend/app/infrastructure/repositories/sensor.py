from adapters.sensor import SensorAdaptor
from core.entities.sensor import Sensor as SensorEntity
from infrastructure.database.tables.sensor import Sensor
from infrastructure.repositories.base import BaseDBRepo


class SensorDBRepository(BaseDBRepo):
    """
    SensorDBRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """

    MODEL = Sensor
    ENTITY = SensorEntity
    ADAPTOR = SensorAdaptor
    TENANT_SCOPE = None  # TODO: no farm linkage in schema; cannot tenant-scope yet

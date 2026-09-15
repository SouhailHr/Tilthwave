from adapters.sensor_record import SensorRecordAdaptor
from core.entities.sensor_record import SensorRecord as SensorRecordEntity
from infrastructure.database.tables.sensor_record import SensorRecord
from infrastructure.repositories.base import BaseDBRepo


class SensorRecordDBRepository(BaseDBRepo):
    """
    SensorDBRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """

    MODEL = SensorRecord
    ENTITY = SensorRecordEntity
    ADAPTOR = SensorRecordAdaptor
    TENANT_SCOPE = None  # TODO: sensor has no farm linkage; cannot tenant-scope yet

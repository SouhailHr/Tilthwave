from adapters.zone import ZoneAdaptor
from core.entities.zone import Zone as ZoneEntity
from infrastructure.database.tables.zone import Zone
from infrastructure.repositories.base import BaseDBRepo


class ZoneDBRepository(BaseDBRepo):
    """
    ZoneDBRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """
    MODEL = Zone
    ENTITY = ZoneEntity
    ADAPTOR = ZoneAdaptor
    TENANT_SCOPE = ("column", "farm_name")

from adapters.farm import FarmAdaptor
from core.entities.farm import Farm as FarmEntity
from infrastructure.database.tables.farm import Farm
from infrastructure.repositories.base import BaseDBRepo


class FarmDBRepository(BaseDBRepo):
    """
    FarmRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """

    MODEL = Farm
    ENTITY = FarmEntity
    ADAPTOR = FarmAdaptor
    TENANT_SCOPE = ("self", "farm_name")

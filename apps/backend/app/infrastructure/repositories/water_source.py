from adapters.water_source import WaterSourceAdaptor
from core.entities.water_source import WaterSource as WaterSourceEntity
from infrastructure.database.tables.water_source import WaterSource
from infrastructure.repositories.base import BaseBrokerRepo, BaseDBRepo


class WaterSourceDBRepository(BaseDBRepo):
    """
    WaterSourceDBRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """

    MODEL = WaterSource
    ENTITY = WaterSourceEntity
    ADAPTOR = WaterSourceAdaptor
    TENANT_SCOPE = ("column", "farm_name")


class WaterSourceBrokerRepository(BaseBrokerRepo):
    """
    WaterSourceBrokerRepository is a Class that Inherits from the Abstract Class BaseBrokerRepo
    """

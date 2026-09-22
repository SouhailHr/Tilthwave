from adapters.water_switcher import WaterSwitcherAdaptor
from core.entities.water_switcher import WaterSwitcher as WaterSwitcherEntity
from infrastructure.database.tables.water_switcher import WaterSwitcher
from infrastructure.repositories.base import BaseBrokerRepo, BaseDBRepo
from infrastructure.repositories.tenancy import TenantScope


class WaterSwitcherDBRepository(BaseDBRepo):
    """
    WaterSwitcherDBRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """

    MODEL = WaterSwitcher
    ENTITY = WaterSwitcherEntity
    ADAPTOR = WaterSwitcherAdaptor
    TENANT_SCOPE = TenantScope.via_zone()


class WaterSwitcherBrokerRepository(BaseBrokerRepo):
    """
    WaterSwitcherBrokerRepository is a Class that Inherits from the Abstract Class BaseBrokerRepo
    """

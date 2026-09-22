from adapters.irrigation_task import IrrigationTaskAdaptor
from core.entities.irrigation_task import IrrigationTask as IrrigationTaskEntity
from infrastructure.database.tables.irrigation_task import IrrigationTask
from infrastructure.repositories.base import BaseDBRepo
from infrastructure.repositories.tenancy import TenantScope


class IrrigationTaskDBRepository(BaseDBRepo):
    """
    IrrigationTaskDBRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """

    MODEL = IrrigationTask
    ENTITY = IrrigationTaskEntity
    ADAPTOR = IrrigationTaskAdaptor
    TENANT_SCOPE = TenantScope.via_zone()

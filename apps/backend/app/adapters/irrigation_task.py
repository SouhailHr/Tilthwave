from adapters.base import BaseAdaptor
from core.entities.irrigation_task import IrrigationTask as IrrigationTaskEntity


class IrrigationTaskAdaptor(BaseAdaptor):
    ENTITY = IrrigationTaskEntity

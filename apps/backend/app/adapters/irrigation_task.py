from adapters.base import BaseAdaptor
from core.entities.irrigation_task import IrrigationTask as IrrigationTaskEntity


class IrrigationTaskAdaptor(BaseAdaptor):
    ENTITY = IrrigationTaskEntity

    BASE_CUSTOM_MAPPER = {
        "created_date": {"field_in_model": "created_date", "convert_to": str},
        "updated_date": {"field_in_model": "updated_date", "convert_to": str},
        "start_time": {"field_in_model": "start_time", "convert_to": str},
    }
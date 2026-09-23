from adapters.irrigation_task import IrrigationTaskAdaptor
from interfaces.api.endpoints.base import BaseCrud, crud_router
from interfaces.api.schemas.irrigation_task import IrrigationTaskCreate, IrrigationTaskUpdate
from wiring import api_use_cases

use_cases = api_use_cases()


class IrrigationTaskCrudHelper(BaseCrud):
    ADAPTOR_CLASS = IrrigationTaskAdaptor
    USE_CASE_INSTANCE = use_cases.irrigation_task
    IDENTIFIER = "zone_name"


router = crud_router(
    "/irrigation-tasks",
    "Irrigation Tasks",
    IrrigationTaskCrudHelper,
    IrrigationTaskCreate,
    IrrigationTaskUpdate,
    noun="irrigation task",
)

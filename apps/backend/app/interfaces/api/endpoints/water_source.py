from adapters.water_source import WaterSourceAdaptor
from interfaces.api.endpoints.base import BaseCrud, crud_router
from interfaces.api.schemas.water_source import WaterSourceCreate, WaterSourceUpdate
from wiring import api_use_cases

use_cases = api_use_cases()


class WaterSourceCrudHelper(BaseCrud):
    ADAPTOR_CLASS = WaterSourceAdaptor
    USE_CASE_INSTANCE = use_cases.water_source
    IDENTIFIER = "serial_number"


router = crud_router(
    "/water-sources", "Water Sources", WaterSourceCrudHelper, WaterSourceCreate, WaterSourceUpdate, noun="water source"
)

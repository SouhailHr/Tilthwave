from adapters.water_switcher import WaterSwitcherAdaptor
from interfaces.api.endpoints.base import BaseCrud, crud_router
from interfaces.api.schemas.water_switcher import WaterSwitcherCreate, WaterSwitcherUpdate
from wiring import api_use_cases

use_cases = api_use_cases()


class WaterSwitcherCrudHelper(BaseCrud):
    ADAPTOR_CLASS = WaterSwitcherAdaptor
    USE_CASE_INSTANCE = use_cases.water_switcher
    IDENTIFIER = "serial_number"


router = crud_router(
    "/water-switchers",
    "Water Switchers",
    WaterSwitcherCrudHelper,
    WaterSwitcherCreate,
    WaterSwitcherUpdate,
    noun="water switcher",
)

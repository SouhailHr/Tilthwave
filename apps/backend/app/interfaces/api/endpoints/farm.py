from adapters.farm import FarmAdaptor
from interfaces.api.endpoints.base import BaseCrud, crud_router
from interfaces.api.schemas.farm import FarmCreate, FarmUpdate
from wiring import api_use_cases

use_cases = api_use_cases()


class FarmCrudHelper(BaseCrud):
    ADAPTOR_CLASS = FarmAdaptor
    USE_CASE_INSTANCE = use_cases.farm
    IDENTIFIER = "farm_name"


router = crud_router("/farms", "Farms", FarmCrudHelper, FarmCreate, FarmUpdate, noun="farm")

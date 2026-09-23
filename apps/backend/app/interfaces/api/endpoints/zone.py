from adapters.zone import ZoneAdaptor
from interfaces.api.endpoints.base import BaseCrud, crud_router
from interfaces.api.schemas.zone import ZoneCreate, ZoneUpdate
from wiring import api_use_cases

use_cases = api_use_cases()


class ZoneCrudHelper(BaseCrud):
    ADAPTOR_CLASS = ZoneAdaptor
    USE_CASE_INSTANCE = use_cases.zone
    IDENTIFIER = "zone_name"


router = crud_router("/zones", "Zones", ZoneCrudHelper, ZoneCreate, ZoneUpdate, noun="zone")

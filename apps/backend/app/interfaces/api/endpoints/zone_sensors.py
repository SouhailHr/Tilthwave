from adapters.zone_sensors import ZoneSensorsAdaptor
from interfaces.api.endpoints.base import BaseCrud, crud_router
from interfaces.api.schemas.zone_sensors import ZoneSensorCreate, ZoneSensorUpdate
from wiring import api_use_cases

use_cases = api_use_cases()


class ZoneSensorsCrudHelper(BaseCrud):
    ADAPTOR_CLASS = ZoneSensorsAdaptor
    USE_CASE_INSTANCE = use_cases.zone_sensors
    IDENTIFIER = "sensor_serial_number"


router = crud_router(
    "/zone-sensors",
    "Zones Sensors",
    ZoneSensorsCrudHelper,
    ZoneSensorCreate,
    ZoneSensorUpdate,
    noun="zone sensor link",
)

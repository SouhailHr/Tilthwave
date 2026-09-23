from adapters.sensor_record import SensorRecordAdaptor
from interfaces.api.endpoints.base import BaseCrud, crud_router
from interfaces.api.schemas.sensor_record import SensorRecordCreate
from wiring import api_use_cases

use_cases = api_use_cases()


class SensorRecordCrudHelper(BaseCrud):
    """Readings normally arrive through the streamer; there is no PATCH, a reading is not edited."""

    ADAPTOR_CLASS = SensorRecordAdaptor
    USE_CASE_INSTANCE = use_cases.sensor_record
    IDENTIFIER = "sensor_serial_number"


router = crud_router(
    "/sensor-records", "Sensor Records", SensorRecordCrudHelper, SensorRecordCreate, noun="sensor record"
)

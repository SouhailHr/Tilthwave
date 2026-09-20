import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.sensor_record import SensorRecordAdaptor
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.sensor_record import SensorRecordCreate
from wiring import api_use_cases

router = APIRouter(prefix="/sensor-records", tags=["Sensor Records"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class SensorRecordCrudHelper(BaseCrud):
    ADAPTOR_CLASS = SensorRecordAdaptor
    USE_CASE_INSTANCE = use_cases.sensor_record
    IDENTIFIER = "sensor_serial_number"


@router.post("/", status_code=201)
def create(data: SensorRecordCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a sensor record (records normally arrive through the streamer)
    """
    return SensorRecordCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=SensorRecordCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of sensor records
    """
    return SensorRecordCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a sensor record by ID
    """
    return SensorRecordCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a sensor record by ID
    """
    return SensorRecordCrudHelper.delete_by_id(id=id)

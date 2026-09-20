import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.zone_sensors import ZoneSensorsAdaptor
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.zone_sensors import ZoneSensorCreate, ZoneSensorUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/zone-sensors", tags=["Zones Sensors"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class ZoneSensorsCrudHelper(BaseCrud):
    ADAPTOR_CLASS = ZoneSensorsAdaptor
    USE_CASE_INSTANCE = use_cases.zone_sensors
    IDENTIFIER = "sensor_serial_number"


@router.post("/", status_code=201)
def create(data: ZoneSensorCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Zone sensor link
    """
    return ZoneSensorsCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=ZoneSensorsCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of Zone sensor links
    """
    return ZoneSensorsCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Zone sensor link by ID
    """
    return ZoneSensorsCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a Zone sensor link by ID
    """
    return ZoneSensorsCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: ZoneSensorUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a Zone sensor link by ID with the given fields
    """
    return ZoneSensorsCrudHelper.update_by_id(id=id, data=data.model_dump(exclude_unset=True), performed_by=username)

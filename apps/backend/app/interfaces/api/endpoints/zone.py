import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.zone import ZoneAdaptor
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.zone import ZoneCreate, ZoneUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/zones", tags=["Zones"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class ZoneCrudHelper(BaseCrud):
    ADAPTOR_CLASS = ZoneAdaptor
    USE_CASE_INSTANCE = use_cases.zone
    IDENTIFIER = "zone_name"


@router.post("/", status_code=201)
def create(data: ZoneCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Zone
    """
    return ZoneCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=ZoneCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of Zones
    """
    return ZoneCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Zone by ID
    """
    return ZoneCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a Zone by ID
    """
    return ZoneCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: ZoneUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a Zone by ID with the given fields
    """
    return ZoneCrudHelper.update_by_id(id=id, data=data.model_dump(exclude_unset=True), performed_by=username)

import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.water_switcher import WaterSwitcherAdaptor
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.water_switcher import WaterSwitcherCreate, WaterSwitcherUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/water-switchers", tags=["Water Switchers"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class WaterSwitcherCrudHelper(BaseCrud):
    ADAPTOR_CLASS = WaterSwitcherAdaptor
    USE_CASE_INSTANCE = use_cases.water_switcher
    IDENTIFIER = "serial_number"


@router.post("/", status_code=201)
def create(data: WaterSwitcherCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Water switcher
    """
    return WaterSwitcherCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=WaterSwitcherCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of Water switchers
    """
    return WaterSwitcherCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/stats/")
def get_stats():
    """
    This Router gets the Water switchers stats
    """
    return WaterSwitcherCrudHelper.get_stats()


@router.get("/select-list/")
def select_list(filters: str | None = Query(None)):
    """
    This Router gets the Water switchers as select options
    """
    return WaterSwitcherCrudHelper.get_select_list(filters_str=filters)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Water switcher by ID
    """
    return WaterSwitcherCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a Water switcher by ID
    """
    return WaterSwitcherCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: WaterSwitcherUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a Water switcher by ID with the given fields
    """
    return WaterSwitcherCrudHelper.update_by_id(id=id, data=data.model_dump(exclude_unset=True), performed_by=username)

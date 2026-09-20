import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.water_source import WaterSourceAdaptor
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.water_source import WaterSourceCreate, WaterSourceUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/water-sources", tags=["Water Sources"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class WaterSourceCrudHelper(BaseCrud):
    ADAPTOR_CLASS = WaterSourceAdaptor
    USE_CASE_INSTANCE = use_cases.water_source
    IDENTIFIER = "serial_number"


@router.post("/", status_code=201)
def create(data: WaterSourceCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Water source
    """
    return WaterSourceCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=WaterSourceCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of Water sources
    """
    return WaterSourceCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/stats/")
def get_stats():
    """
    This Router gets the Water sources stats
    """
    return WaterSourceCrudHelper.get_stats()


@router.get("/select-list/")
def select_list(filters: str | None = Query(None)):
    """
    This Router gets the Water sources as select options
    """
    return WaterSourceCrudHelper.get_select_list(filters_str=filters)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Water source by ID
    """
    return WaterSourceCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a Water source by ID
    """
    return WaterSourceCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: WaterSourceUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a Water source by ID with the given fields
    """
    return WaterSourceCrudHelper.update_by_id(id=id, data=data.model_dump(exclude_unset=True), performed_by=username)

import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.farm import FarmAdaptor
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.farm import FarmCreate, FarmUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/farms", tags=["Farms"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class FarmCrudHelper(BaseCrud):
    ADAPTOR_CLASS = FarmAdaptor
    USE_CASE_INSTANCE = use_cases.farm
    IDENTIFIER = "farm_name"


@router.post("/", status_code=201)
def create(data: FarmCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Farm
    """
    return FarmCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=FarmCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of Farms
    """
    return FarmCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Farm by ID
    """
    return FarmCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a Farm by ID
    """
    return FarmCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: FarmUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a Farm by ID with the given fields
    """
    return FarmCrudHelper.update_by_id(id=id, data=data.model_dump(exclude_unset=True), performed_by=username)

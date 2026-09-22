import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.irrigation_task import IrrigationTaskAdaptor
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.irrigation_task import IrrigationTaskCreate, IrrigationTaskUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/irrigation-tasks", tags=["Irrigation Tasks"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class IrrigationTaskCrudHelper(BaseCrud):
    ADAPTOR_CLASS = IrrigationTaskAdaptor
    USE_CASE_INSTANCE = use_cases.irrigation_task
    IDENTIFIER = "zone_name"


@router.post("/", status_code=201)
def create(data: IrrigationTaskCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Irrigation task
    """
    return IrrigationTaskCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=IrrigationTaskCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of Irrigation tasks
    """
    return IrrigationTaskCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Irrigation task by ID
    """
    return IrrigationTaskCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a Irrigation task by ID
    """
    return IrrigationTaskCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: IrrigationTaskUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a Irrigation task by ID with the given fields
    """
    return IrrigationTaskCrudHelper.update_by_id(id=id, data=data.model_dump(exclude_unset=True), performed_by=username)

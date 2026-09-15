import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.irrigation_task import IrrigationTaskAdaptor
from config.settings import settings
from core.use_cases.irrigation_task import IrrigationTaskUseCase
from infrastructure.repositories.irrigation_task import IrrigationTaskDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.irrigation_task import IrrigationTaskCreate

router = APIRouter(prefix="/irrigation-tasks", tags=["Irrigation Tasks"])
IrrigationTask_repo = IrrigationTaskDBRepository(uri=settings.DATABASE.URI)
IrrigationTask_use_case = IrrigationTaskUseCase(repo=IrrigationTask_repo)
logger = logging.getLogger(__name__)


class IrrigationTaskCrudHelper(BaseCrud):
    ADAPTOR_CLASS = IrrigationTaskAdaptor
    USE_CASE_INSTANCE = IrrigationTask_use_case
    IDENTIFIER = "zone_name"


@router.post("/")
def create(data: IrrigationTaskCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a IrrigationTask
    """
    return IrrigationTaskCrudHelper.create(data=data, performed_by=username)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a IrrigationTask by ID
    """
    return IrrigationTaskCrudHelper.get_by_id(id=id)


@router.get("/", response_model=Page[dict])
def get_all(filters: Optional[str] = Query(None)):
    """
    This Router gets all the Irrigation Tasks
    """
    return IrrigationTaskCrudHelper.get_all(filters_str=filters)


@router.get("/stats/")
def get_irrigation_tasks_stats():
    """
    This Router gets all the Irrigation tasks stats
    """
    return IrrigationTaskCrudHelper.get_stats()


@router.get("/select-list/")
def select_list():
    """
    This Router for the select list
    """
    return IrrigationTaskCrudHelper.get_select_list()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a IrrigationTask by ID
    """
    return IrrigationTaskCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a IrrigationTask by ID with the given Data
    """
    return IrrigationTaskCrudHelper.update_by_id(id=id, data=data, performed_by=username)

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.water_switcher import WaterSwitcherAdaptor
from config.settings import settings
from core.use_cases.water_switcher import WaterSwitcherUseCase
from infrastructure.repositories.sensor import SensorDBRepository
from infrastructure.repositories.water_switcher import WaterSwitcherDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.water_switcher import WaterSwitcherCreate

router = APIRouter(prefix="/water-switchers", tags=["Water Switchers"])
water_switcher_repo = WaterSwitcherDBRepository(uri=settings.DATABASE.URI)
sensor_repo = SensorDBRepository(uri=settings.DATABASE.URI)
water_switcher_use_case = WaterSwitcherUseCase(repo=water_switcher_repo, sensor_repo=sensor_repo)
logger = logging.getLogger(__name__)


class WaterSwitcherCrudHelper(BaseCrud):
    ADAPTOR_CLASS = WaterSwitcherAdaptor
    USE_CASE_INSTANCE = water_switcher_use_case
    IDENTIFIER = "serial_number"


@router.post("/")
def create(data: WaterSwitcherCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a water_switcher
    """
    return WaterSwitcherCrudHelper.create(data=data, performed_by=username)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a water_switcher by ID
    """
    return WaterSwitcherCrudHelper.get_by_id(id=id)


@router.get("/", response_model=Page[dict])
def get_all(filters: Optional[str] = Query(None)):
    """
    This Router gets all the water_switchers
    """
    return WaterSwitcherCrudHelper.get_all(filters)


@router.get("/stats/")
def get_water_switcher_stats():
    """
    This Router gets all the Water Switchers stats
    """
    return WaterSwitcherCrudHelper.get_stats()


@router.get("/select-list/")
def select_list():
    """
    This Router gets all Zone for the select list
    """
    return WaterSwitcherCrudHelper.get_select_list()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a water_switcher by ID
    """
    return WaterSwitcherCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a water_switcher by ID with the given Data
    """
    return WaterSwitcherCrudHelper.update_by_id(id=id, data=data, performed_by=username)

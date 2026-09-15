import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.water_source import WaterSourceAdaptor
from config.settings import settings
from core.use_cases.water_source import WaterSourceUseCase
from infrastructure.repositories.sensor import SensorDBRepository
from infrastructure.repositories.water_source import WaterSourceDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.water_source import WaterSourceCreate

router = APIRouter(prefix="/water-sources", tags=["Water Sources"])
water_source_repo = WaterSourceDBRepository(uri=settings.DATABASE.URI)
sensor_repo = SensorDBRepository(uri=settings.DATABASE.URI)
water_source_use_case = WaterSourceUseCase(repo=water_source_repo,
                                           sensor_repo=sensor_repo,
                                           sensor_record_repo=None, broker_repo=None)
logger = logging.getLogger(__name__)


class WaterSourceCrudHelper(BaseCrud):
    ADAPTOR_CLASS = WaterSourceAdaptor
    USE_CASE_INSTANCE = water_source_use_case
    IDENTIFIER = "serial_number"


@router.post("/")
def create(data: WaterSourceCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a water_source
    """
    return WaterSourceCrudHelper.create(data=data, performed_by=username)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a water_source by ID
    """
    return WaterSourceCrudHelper.get_by_id(id=id)


@router.get("/", response_model=Page[dict])
def get_all(filters: Optional[str] = Query(None)):
    """
    This Router gets all the water_sources
    """
    return WaterSourceCrudHelper.get_all(filters_str=filters)


@router.get("/stats/")
def get_water_sources_stats():
    """
    This Router gets all the Water Sources stats
    """
    return WaterSourceCrudHelper.get_stats()


@router.get("/select-list/")
def select_list():
    """
    This Router  for the select list
    """
    return WaterSourceCrudHelper.get_select_list()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a water_source by ID
    """
    return WaterSourceCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a water_source by ID with the given Data
    """
    return WaterSourceCrudHelper.update_by_id(id=id, data=data, performed_by=username)

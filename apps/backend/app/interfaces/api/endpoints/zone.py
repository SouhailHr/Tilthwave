import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.zone import ZoneAdaptor
from config.settings import settings
from core.use_cases.zone import ZoneUseCase
from infrastructure.repositories.irrigation_task import IrrigationTaskDBRepository
from infrastructure.repositories.sensor import SensorDBRepository
from infrastructure.repositories.sensor_record import SensorRecordDBRepository
from infrastructure.repositories.tree import TreeDBRepository
from infrastructure.repositories.water_switcher import WaterSwitcherDBRepository
from infrastructure.repositories.zone import ZoneDBRepository
from infrastructure.repositories.zone_sensors import ZoneSensorsDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.zone import ZoneCreate

router = APIRouter(prefix="/zones", tags=["Zones"])
# Getting all the repos to use in zone use case

irrigation_task_repo = IrrigationTaskDBRepository(uri=settings.DATABASE.URI)
zone_sensors_repo = ZoneSensorsDBRepository(uri=settings.DATABASE.URI)
sensor_repo = SensorDBRepository(uri=settings.DATABASE.URI)
sensor_records_repo = SensorRecordDBRepository(uri=settings.DATABASE.URI)
zone_repo = ZoneDBRepository(uri=settings.DATABASE.URI)
water_switcher_repo = WaterSwitcherDBRepository(uri=settings.DATABASE.URI)
tree_repo = TreeDBRepository(uri=settings.DATABASE.URI)
# Getting the zones to check triggers
zone_use_case = ZoneUseCase(repo=zone_repo,
                            irrigation_task_repo=irrigation_task_repo,
                            zone_sensors_repo=zone_sensors_repo,
                            sensor_repo=sensor_repo,
                            sensor_record_repo=sensor_records_repo,
                            water_switcher_repo=water_switcher_repo,
                            water_source_repo=None,
                            tree_repo=tree_repo)

logger = logging.getLogger(__name__)


class ZoneCrudHelper(BaseCrud):
    ADAPTOR_CLASS = ZoneAdaptor
    USE_CASE_INSTANCE = zone_use_case
    IDENTIFIER = "zone_name"


@router.post("/")
def create(data: ZoneCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Zone
    """
    return ZoneCrudHelper.create(data=data, performed_by=username)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Zone by ID
    """
    return ZoneCrudHelper.get_by_id(id=id)


@router.get("/identifier/{identifier}")
def get_by_identifier(identifier: str):
    """
    This Router gets a zone by zone identifier
    """
    return ZoneCrudHelper.get_by_identifier(identifier=identifier)


@router.get("/", response_model=Page[dict])
def get_all(filters: Optional[str] = Query(None)):
    """
    This Router gets all the Zones
    """
    return ZoneCrudHelper.get_all(filters_str=filters)


@router.get("/select-list/")
def select_list():
    """
    This Router gets all Zone for the select list
    """
    # list_data = [{"value": zone_name, "label":  zone_name }]
    return ZoneCrudHelper.get_select_list()


@router.get("/stats/{zone_name}")
def get_zone_stats(zone_name: str):
    """
    This Router gets all stats per zone
    """
    return ZoneCrudHelper.get_stats(entity_name=zone_name)


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a Zone by ID
    """
    return ZoneCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a Zone by ID with the given Data
    """
    return ZoneCrudHelper.update_by_id(id=id, data=data, performed_by=username)

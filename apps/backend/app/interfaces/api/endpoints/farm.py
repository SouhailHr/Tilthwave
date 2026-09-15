import logging

from fastapi import APIRouter, Depends
from fastapi_pagination import Page
from adapters.farm import FarmAdaptor
from config.settings import settings
from core.use_cases.farm import FarmUseCase
from infrastructure.repositories.farm import FarmDBRepository
from infrastructure.repositories.sensor_record import SensorRecordDBRepository
from infrastructure.repositories.tree import TreeDBRepository
from infrastructure.repositories.water_source import WaterSourceDBRepository
from infrastructure.repositories.water_switcher import WaterSwitcherDBRepository
from infrastructure.repositories.zone import ZoneDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.farm import FarmCreate

router = APIRouter(prefix="/farms", tags=["Farms"])
farm_repo = FarmDBRepository(uri=settings.DATABASE.URI)
zone_repo = ZoneDBRepository(uri=settings.DATABASE.URI)
water_source_repo = WaterSourceDBRepository(uri=settings.DATABASE.URI)
water_switcher_repo = WaterSwitcherDBRepository(uri=settings.DATABASE.URI)
tree_repo = TreeDBRepository(uri=settings.DATABASE.URI)
sensor_record_repo = SensorRecordDBRepository(uri=settings.DATABASE.URI)
farm_use_case = FarmUseCase(repo=farm_repo,
                            zone_repo=zone_repo,
                            water_source_repo=water_source_repo,
                            water_switcher_repo=water_switcher_repo,
                            tree_repo=tree_repo,sensor_record_repo=sensor_record_repo)
logger = logging.getLogger(__name__)


class FarmCrudHelper(BaseCrud):
    ADAPTOR_CLASS = FarmAdaptor
    USE_CASE_INSTANCE = farm_use_case
    IDENTIFIER = "farm_name"


@router.post("/")
def create(data: FarmCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a farm
    """
    return FarmCrudHelper.create(data=data, performed_by=username)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a farm by ID
    """
    return FarmCrudHelper.get_by_id(id=id)


@router.get("/identifier/{identifier}")
def get_by_identifier(identifier: str):
    """
    This Router gets a farm by farm name
    """
    return FarmCrudHelper.get_by_identifier(identifier=identifier)


@router.get("/", response_model=Page[dict])
def get_all():
    """
    This Router gets all the Farms
    """
    return FarmCrudHelper.get_all()


@router.get("/stats/{farm_name}")
def get_farm_stats(farm_name: str):
    """
    This Router gets all the Farm stats
    """
    return FarmCrudHelper.get_stats(entity_name=farm_name)


@router.get("/select-list/")
def select_list():
    """
    This Router gets all farm for the select list
    """
    return FarmCrudHelper.get_select_list()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a farm by ID
    """
    return FarmCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a farm by ID with the given Data
    """
    return FarmCrudHelper.update_by_id(id=id, data=data, performed_by=username)



import logging

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from adapters.zone_sensors import ZoneSensorsAdaptor
from config.settings import settings
from core.use_cases.zone_sensors import ZoneSensorsUseCase
from infrastructure.repositories.sensor import SensorDBRepository
from infrastructure.repositories.zone_sensors import ZoneSensorsDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.zone_sensors import ZoneSensorCreate

router = APIRouter(prefix="/zone-sensors", tags=["Zones Sensors"])
zone_sensors_repo = ZoneSensorsDBRepository(uri=settings.DATABASE.URI)
sensor_repo = SensorDBRepository(uri=settings.DATABASE.URI)
zone_sensors_use_case = ZoneSensorsUseCase(repo=zone_sensors_repo, sensor_repo=sensor_repo,)
logger = logging.getLogger(__name__)


class ZoneSensorsCrudHelper(BaseCrud):
    ADAPTOR_CLASS = ZoneSensorsAdaptor
    USE_CASE_INSTANCE = zone_sensors_use_case


@router.post("/")
def create(data: ZoneSensorCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Sensor for a Zone
    """
    return ZoneSensorsCrudHelper.create(data=data, performed_by=username)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Zone Sensor by ID
    """
    return ZoneSensorsCrudHelper.get_by_id(id=id)


@router.get("/", response_model=Page[dict])
def get_all():
    """
    This Router gets all the Zones Sensors
    """
    return ZoneSensorsCrudHelper.get_all()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a Zone Sensor by ID
    """
    return ZoneSensorsCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a Zone Sensor by ID with the given Data
    """
    return ZoneSensorsCrudHelper.update_by_id(id=id, data=data, performed_by=username)

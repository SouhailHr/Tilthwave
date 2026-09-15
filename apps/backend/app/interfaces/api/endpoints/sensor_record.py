import logging

from fastapi import APIRouter
from fastapi_pagination import Page

from adapters.sensor_record import SensorRecordAdaptor
from config.settings import settings
from core.use_cases.sensor_record import SensorRecordUseCase
from infrastructure.repositories.sensor_record import SensorRecordDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.schemas.sensor_record import SensorRecordCreate

router = APIRouter(prefix="/sensor-records", tags=["Sensor Records"])
sensor_record_repo = SensorRecordDBRepository(uri=settings.DATABASE.URI)
sensor_record_use_case = SensorRecordUseCase(repo=sensor_record_repo)
logger = logging.getLogger(__name__)


class SensorRecordCrudHelper(BaseCrud):
    ADAPTOR_CLASS = SensorRecordAdaptor
    USE_CASE_INSTANCE = sensor_record_use_case


@router.post("/")
def create(data: SensorRecordCreate):
    """
    This Router creates a sensor record
    """
    return SensorRecordCrudHelper.create(data=data)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a sensor record by ID
    """
    return SensorRecordCrudHelper.get_by_id(id=id)


@router.get("/", response_model=Page[dict])
def get_all():
    """
    This Router gets all the sensors records
    """
    return SensorRecordCrudHelper.get_all()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a sensor record by ID
    """
    return SensorRecordCrudHelper.delete_by_id(id=id)

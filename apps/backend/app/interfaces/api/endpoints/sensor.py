import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from interfaces.api.endpoints.sensor_base import SensorCrudHelper
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.sensor import SensorCreate

router = APIRouter(prefix="/sensors", tags=["Sensor"])

logger = logging.getLogger(__name__)


@router.post("/")
def create(data: SensorCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a sensor
    """
    # TODO souhail something goes for create we can send a zone_name / switcher or source  serial number

    return SensorCrudHelper.create(data=data, performed_by=username)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a sensor by ID
    """
    return SensorCrudHelper.get_by_id(id=id)


@router.get("/", response_model=Page[dict])
def get_all(filters: Optional[str] = Query(None)):
    """
    This Router gets all the sensors.
    """
    return SensorCrudHelper.get_all(filters_str=filters)


@router.get("/select-list/")
def select_list():
    """
    This Router for the select list
    """
    return SensorCrudHelper.get_select_list()


@router.get("/stats/")
def get_sensors_stats():
    """
    This Router gets all the sensors stats
    """
    return SensorCrudHelper.get_stats()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a sensor by ID
    """
    return SensorCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a sensor by ID with the given Data
    """
    # TODO souhail something goes for update we can send a zone_name / switcher or source  serial number
    return SensorCrudHelper.update_by_id(id=id, data=data, performed_by=username)

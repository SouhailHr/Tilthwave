import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from interfaces.api.endpoints.sensor_base import SensorCrudHelper
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.sensor import SensorCreate, SensorUpdate

router = APIRouter(prefix="/sensors", tags=["Sensor"])
logger = logging.getLogger(__name__)


@router.post("/", status_code=201)
def create(data: SensorCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a sensor and, per assigned_to_type, its link to a zone / switcher / source
    """
    return SensorCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=SensorCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of sensors, each with its `assigned_to`
    """
    return SensorCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a sensor by ID
    """
    return SensorCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a sensor by ID
    """
    return SensorCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: SensorUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a sensor by ID and, per assigned_to_type, its link to a zone / switcher / source
    """
    return SensorCrudHelper.update_by_id(id=id, data=data.model_dump(exclude_unset=True), performed_by=username)

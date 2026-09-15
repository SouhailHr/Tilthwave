import logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.tree import TreeAdaptor
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.tree import TreeCreate, TreeUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/trees", tags=["Trees"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class TreeCrudHelper(BaseCrud):
    ADAPTOR_CLASS = TreeAdaptor
    USE_CASE_INSTANCE = use_cases.tree
    IDENTIFIER = "serial_number"


@router.post("/", status_code=201)
def create(data: TreeCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Tree
    """
    return TreeCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=TreeCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of Trees
    """
    return TreeCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/stats/")
def get_stats():
    """
    This Router gets the Trees stats
    """
    return TreeCrudHelper.get_stats()


@router.get("/select-list/")
def select_list(filters: str | None = Query(None)):
    """
    This Router gets the Trees as select options
    """
    return TreeCrudHelper.get_select_list(filters_str=filters)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Tree by ID
    """
    return TreeCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a Tree by ID
    """
    return TreeCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: TreeUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a Tree by ID with the given fields
    """
    return TreeCrudHelper.update_by_id(id=id, data=data.model_dump(exclude_unset=True), performed_by=username)

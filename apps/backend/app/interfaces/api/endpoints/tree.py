import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page

from adapters.tree import TreeAdaptor
from config.settings import settings
from core.use_cases.tree import TreeUseCase
from infrastructure.repositories.tree import TreeDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.tree import TreeCreate

router = APIRouter(prefix="/trees", tags=["Trees"])
tree_repo = TreeDBRepository(uri=settings.DATABASE.URI)
tree_use_case = TreeUseCase(repo=tree_repo)
logger = logging.getLogger(__name__)


class TreeCrudHelper(BaseCrud):
    ADAPTOR_CLASS = TreeAdaptor
    USE_CASE_INSTANCE = tree_use_case
    IDENTIFIER = "serial_number"


@router.post("/")
def create(data: TreeCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a Tree
    """
    return TreeCrudHelper.create(data=data, performed_by=username)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a Tree by ID
    """
    return TreeCrudHelper.get_by_id(id=id)


@router.get("/", response_model=Page[dict])
def get_all(filters: Optional[str] = Query(None)):
    """
    This Router gets all the Trees
    """
    return TreeCrudHelper.get_all(filters_str=filters)


@router.get("/stats/")
def get_trees_stats():
    """
    This Router gets all the trees stats
    """
    return TreeCrudHelper.get_stats()


@router.get("/select-list/")
def select_list():
    """
    This Router for the select list
    """
    return TreeCrudHelper.get_select_list()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a Tree by ID
    """
    return TreeCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a Tree by ID with the given Data
    """
    return TreeCrudHelper.update_by_id(id=id, data=data, performed_by=username)

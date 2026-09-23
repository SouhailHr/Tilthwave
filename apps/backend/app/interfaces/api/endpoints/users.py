import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from fastapi_pagination import Page
from starlette import status

from adapters.users import UserAdaptor
from core.security.password import PasswordHasher
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.users import UserCreate, UserUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/users", tags=["Users"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class UserCrudHelper(BaseCrud):
    ADAPTOR_CLASS = UserAdaptor
    USE_CASE_INSTANCE = use_cases.users
    IDENTIFIER = "username"

    @classmethod
    def create(cls, data: UserCreate, performed_by=None):
        """
        Same as BaseCrud.create, but the plain password is replaced by its hash first and
        never reaches the entity.
        """
        payload = data.model_dump()  # `password` is excluded by the schema
        payload["password"] = PasswordHasher.hash(payload.pop("text_password"))
        payload["performed_by"] = performed_by
        entity = cls.ADAPTOR_CLASS.dict_to_entity(payload)
        result = cls.USE_CASE_INSTANCE.create(entity)
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=result.to_public_dict())


@router.post("/", status_code=201)
def create(data: UserCreate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router creates a User
    """
    return UserCrudHelper.create(data=data, performed_by=username)


@router.get("/", response_model=Page[dict])
def get_all(
    filters: str | None = Query(None, description=UserCrudHelper.filters_doc()),
    search: str | None = Query(None, description="Case-insensitive match on the identifier"),
):
    """
    This Router gets one page of Users
    """
    return UserCrudHelper.get_all(filters_str=filters, search=search)


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a User by ID
    """
    return UserCrudHelper.get_by_id(id=id)


@router.delete("/{id}", status_code=204)
def delete_by_id(id: int):
    """
    This Router deletes a User by ID
    """
    return UserCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: UserUpdate, username: str = Depends(AuthHelper.get_current_user_username)):
    """
    This Router updates a User by ID with the given fields
    """
    payload = data.model_dump(exclude_unset=True)
    text_password = payload.pop("text_password", None)
    if text_password:
        payload["password"] = PasswordHasher.hash(text_password)
    return UserCrudHelper.update_by_id(id=id, data=payload, performed_by=username)

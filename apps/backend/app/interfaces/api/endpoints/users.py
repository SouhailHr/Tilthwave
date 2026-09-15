import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi import Query
from typing import Optional

from starlette import status
from starlette.responses import JSONResponse

from adapters.users import UserAdaptor
from config.settings import settings
from core.use_cases.users import UserUseCase
from infrastructure.repositories.users import UserDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.users import UserCreate

router = APIRouter(prefix="/users", tags=["Users"])
user_repo = UserDBRepository(uri=settings.DATABASE.URI)
user_use_case = UserUseCase(repo=user_repo)
logger = logging.getLogger(__name__)


class UserCrudHelper(BaseCrud):
    ADAPTOR_CLASS = UserAdaptor
    USE_CASE_INSTANCE = user_use_case
    IDENTIFIER = "username"

    @classmethod
    def create(cls, data, performed_by=None):
        """
        logic:
            1- Get input from user and the username of the current user
            2- Transform input to dict
            3- Transform input from dict to entity
            4- Create an object using its use case
        @param data:
        @param performed_by:
        @return Dict of the object
        """
        try:
            data = data.model_dump()
            data['performed_by'] = performed_by  # Set the username
            # remove text password from the data
            if data.get('text_password'):
                data.pop("text_password", None)
            entity = cls.ADAPTOR_CLASS.dict_to_entity(data)
            result = cls.USE_CASE_INSTANCE.create(entity)
            if result:
                return JSONResponse(status_code=status.HTTP_200_OK, content=result.to_dict())
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
def create(data: UserCreate):
    """
    This Router creates a User
    """
    hashed_password = AuthHelper.get_password_hash(data.text_password)
    data.password = hashed_password
    return UserCrudHelper.create(data=data, performed_by="username")


@router.get("/{id}")
def get_by_id(id: int):
    """
    This Router gets a User by ID
    """
    return UserCrudHelper.get_by_id(id=id)


@router.get("/", response_model=Page[dict])
def get_all(filters: Optional[str] = Query(None)):
    """
    This Router gets all the Users
    """
    return UserCrudHelper.get_all(filters)


@router.get("/stats/")
def get_users_stats():
    """
    This Router gets all the Users stats
    """
    return UserCrudHelper.get_stats()


@router.get("/select-list/")
def select_list():
    """
    This Router for the select list
    """
    return UserCrudHelper.get_select_list()


@router.delete("/{id}")
def delete_by_id(id: int):
    """
    This Router deletes a User by ID
    """
    return UserCrudHelper.delete_by_id(id=id)


@router.patch("/{id}")
def update_by_id(id: int, data: dict, username: str = Depends(AuthHelper.get_current_user_username)):
    """
     This Router updates a User by ID with the given Data
    """
    # Hash the text password if provided securely before updating the user record
    if data.get('text_password'):
        data['password'] = AuthHelper.get_password_hash(data['text_password'])
        # drop text password
        data.pop("text_password", None)
    return UserCrudHelper.update_by_id(id=id, data=data, performed_by=username)

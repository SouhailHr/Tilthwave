import logging

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from adapters.users import UserAdaptor
from config.settings import settings
from core.use_cases.users import UserUseCase
from infrastructure.repositories.users import UserDBRepository
from interfaces.api.endpoints.base import BaseCrud
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.schemas.auth import AuthLogin, AuthVerifyToken

router = APIRouter(prefix="/auth", tags=["Auth"])
user_repo = UserDBRepository(uri=settings.DATABASE.URI)
user_use_case = UserUseCase(repo=user_repo)
logger = logging.getLogger(__name__)


class UserCrudHelper(BaseCrud):
    ADAPTOR_CLASS = UserAdaptor
    USE_CASE_INSTANCE = user_use_case


@router.post("/login")
def login(data: AuthLogin):
    """
    Router for Login

    """
    user = user_use_case.authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    # Prepare data for JWT token
    token_data = {
        "role": user.role,
        "username": user.username,
        "user_id": user.id,
        "user_full_name": f"{user.first_name} {user.last_name}",
        "farm_name": user.farm_name,  # tenant claim for per-farm object scoping
    }
    access_token = AuthHelper.create_access_token(data=token_data)
    return JSONResponse(content={"token": access_token, "token_type": "bearer"})


@router.post("/token/verify/")
def verify_access_token(data: AuthVerifyToken):
    """
    Router for Verifying access token

    """
    return AuthHelper.verify_access_token(data.token)

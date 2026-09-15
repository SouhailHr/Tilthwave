import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette import status

from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.helpers.rate_limit import limit_login_attempts
from interfaces.api.schemas.auth import AuthLogin, AuthVerifyToken
from wiring import api_use_cases

router = APIRouter(prefix="/auth", tags=["Auth"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


@router.post("/login", dependencies=[Depends(limit_login_attempts)])
def login(data: AuthLogin):
    """
    Router for Login. Rate limited per client IP (API_LOGIN_RATE_LIMIT_PER_MINUTE).
    """
    user = use_cases.users.authenticate_user(data.username, data.password)
    if not user or not user.is_active:
        # 400 (not 401) on purpose: the web client treats 401 as "session expired".
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
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

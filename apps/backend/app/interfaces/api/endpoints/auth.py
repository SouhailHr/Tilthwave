import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette import status

from config.settings import settings
from interfaces.api.helpers.auth import CLAIMS_STATE_KEY, AuthHelper
from interfaces.api.helpers.cookies import clear_session_cookies, new_csrf_token, set_session_cookies
from interfaces.api.helpers.rate_limit import limit_login_attempts
from interfaces.api.helpers.tenant import TOKEN_INVALID_STATE_KEY
from interfaces.api.schemas.auth import AuthLogin, AuthVerifyToken
from wiring import api_use_cases

router = APIRouter(prefix="/auth", tags=["Auth"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)


@router.post("/login", dependencies=[Depends(limit_login_attempts)])
def login(data: AuthLogin):
    """
    Router for Login. Rate limited per client IP (API_LOGIN_RATE_LIMIT_PER_MINUTE).

    API clients get the token in the body and send it back as Authorization: Bearer. The web app
    sends use_cookie=true and gets the session as httpOnly cookies instead (helpers/cookies.py):
    the token is then never in a body JavaScript can read, which is the point.
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
    if data.use_cookie:
        response = JSONResponse(content={"token_type": "cookie", "expires_in": settings.API.ACCESS_TOKEN_EXPIRE * 60})
        set_session_cookies(response, access_token, new_csrf_token())
        return response
    return JSONResponse(content={"token": access_token, "token_type": "bearer"})


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    """
    Clear the browser session cookies. Bearer clients have nothing to clear (the token simply
    expires); for them this is a harmless no-op.
    """
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookies(response)
    return response


@router.get("/me")
def me(request: Request):
    """
    The caller's identity as TenantContextMiddleware established it: credential verified, user
    row loaded and active, role and farm from the database. This is how the web app learns
    whether it is signed in, since it cannot read its own httpOnly session cookie.
    """
    if getattr(request.state, TOKEN_INVALID_STATE_KEY, False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = getattr(request.state, CLAIMS_STATE_KEY, None)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "user_id": claims.get("user_id"),
        "username": claims.get("username"),
        "role": claims.get("role"),
        "farm_name": claims.get("farm_name"),
        "exp": claims.get("exp"),
    }


@router.post("/token/verify/")
def verify_access_token(data: AuthVerifyToken):
    """
    Router for Verifying access token
    """
    return AuthHelper.verify_access_token(data.token)

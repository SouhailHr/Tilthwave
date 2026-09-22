"""
The caller's own account: profile and password. Self-service for every role, own row only - the
user_id comes from the verified session, never from the request.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette import status

from common.exceptions import NotFoundError
from config.settings import settings
from interfaces.api.helpers.auth import CLAIMS_STATE_KEY, AuthHelper
from interfaces.api.helpers.cookies import new_csrf_token, set_session_cookies
from interfaces.api.helpers.tenant import AUTH_VIA_STATE_KEY
from interfaces.api.schemas.account import PasswordChange, ProfileUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/account", tags=["Account"])
use_cases = api_use_cases()


def _user_id(request: Request) -> int:
    # RBACMiddleware already guaranteed a verified session with claims for every /account route.
    return getattr(request.state, CLAIMS_STATE_KEY)["user_id"]


@router.get("/profile")
def get_profile(request: Request):
    """The caller's own user record (password hash never included)."""
    user = use_cases.users.get_own(_user_id(request))
    if user is None:
        raise NotFoundError("Users not found")
    return user.to_public_dict()


@router.patch("/profile")
def update_profile(
    request: Request, data: ProfileUpdate, username: str = Depends(AuthHelper.get_current_user_username)
):
    """Update the caller's own contact details. Role, farm and active flag are not editable here."""
    payload = data.model_dump(exclude_unset=True)
    payload["performed_by"] = username
    user = use_cases.users.update_own_profile(_user_id(request), payload)
    if user is None:
        raise NotFoundError("Users not found")
    return user.to_public_dict()


@router.post("/password")
def change_password(request: Request, data: PasswordChange):
    """
    Change the caller's own password after verifying the current one.

    Every other session of this user stops verifying immediately (their tokens carry the old
    password fingerprint). This session is re-issued in the same response so the caller stays
    signed in: new cookies for a browser session, a new bearer token for an API client.
    """
    user = use_cases.users.change_password(_user_id(request), data.current_password, data.new_password)
    access_token = AuthHelper.create_access_token(AuthHelper.session_claims(user))
    # Same shape as /auth/login plus the message: token is null when the session travels as a cookie.
    expires_in = settings.API.ACCESS_TOKEN_EXPIRE * 60
    if getattr(request.state, AUTH_VIA_STATE_KEY, None) == "cookie":
        body = {"message": "Password changed", "token": None, "token_type": "cookie", "expires_in": expires_in}
        response = JSONResponse(status_code=status.HTTP_200_OK, content=body)
        set_session_cookies(response, access_token, new_csrf_token())
        return response
    body = {"message": "Password changed", "token": access_token, "token_type": "bearer", "expires_in": expires_in}
    return JSONResponse(status_code=status.HTTP_200_OK, content=body)

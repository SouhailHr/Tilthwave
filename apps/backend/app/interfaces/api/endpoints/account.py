"""
The caller's own account: profile, password and sessions. Self-service for every role, own row only
- the user_id comes from the verified session, never from the request.
"""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from starlette import status

from common.audit import audit
from common.exceptions import NotFoundError
from interfaces.api.helpers.auth import CLAIMS_STATE_KEY, AuthHelper
from interfaces.api.helpers.cookies import new_csrf_token, set_session_cookies
from interfaces.api.helpers.rate_limit import client_ip
from interfaces.api.helpers.tenant import AUTH_VIA_STATE_KEY
from interfaces.api.schemas.account import PasswordChange, ProfileUpdate
from wiring import api_use_cases

router = APIRouter(prefix="/account", tags=["Account"])
use_cases = api_use_cases()


def _claims(request: Request) -> dict:
    # RBACMiddleware already guaranteed a verified session with claims for every /account route.
    return getattr(request.state, CLAIMS_STATE_KEY)


def _user_id(request: Request) -> int:
    return _claims(request)["user_id"]


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
    """
    Update the caller's own contact details. Role, farm and active flag are not editable here; a
    new email needs `current_password`.
    """
    payload = data.model_dump(exclude_unset=True)  # current_password is excluded by the schema
    payload["performed_by"] = username
    user = use_cases.users.update_own_profile(_user_id(request), payload, data.current_password)
    if user is None:
        raise NotFoundError("Users not found")
    return user.to_public_dict()


@router.post("/password")
def change_password(request: Request, data: PasswordChange):
    """
    Change the caller's own password after verifying the current one.

    Every session of this user is ended, this one included, and a fresh one is opened in the same
    response so the caller stays signed in: new cookies for a browser session, a new bearer token
    for an API client. Every other device is signed out at its next request.
    """
    user = use_cases.users.change_password(_user_id(request), data.current_password, data.new_password)
    audit("account.password_change", user=user.username, ip=client_ip(request))
    channel = getattr(request.state, AUTH_VIA_STATE_KEY, None)
    access_token = AuthHelper.open_session(user, channel or "header", request)
    # Same shape as /auth/login plus the message: token is null when the session travels as a cookie.
    expires_in = AuthHelper.session_lifetime_seconds()
    if channel == "cookie":
        body = {"message": "Password changed", "token": None, "token_type": "cookie", "expires_in": expires_in}
        response = JSONResponse(status_code=status.HTTP_200_OK, content=body)
        set_session_cookies(response, access_token, new_csrf_token())
        return response
    body = {"message": "Password changed", "token": access_token, "token_type": "bearer", "expires_in": expires_in}
    return JSONResponse(status_code=status.HTTP_200_OK, content=body)


def _session_view(session, current_id: int) -> dict:
    return {**session.to_public_dict(), "current": session.id == current_id}


@router.get("/sessions")
def list_sessions(request: Request):
    """
    The caller's live sessions (this one flagged `current`), newest first: where and since when
    they are signed in. A session that was signed out or timed out is not listed.
    """
    claims = _claims(request)
    sessions = use_cases.sessions.live_for(claims["user_id"])
    return {"items": [_session_view(s, claims["session_id"]) for s in sessions]}


@router.delete("/sessions", status_code=status.HTTP_200_OK)
def revoke_other_sessions(request: Request):
    """Sign out everywhere else: every session of the caller but this one is ended."""
    claims = _claims(request)
    revoked = use_cases.sessions.revoke_all(claims["user_id"], except_token_id=claims["jti"])
    audit("session.revoke_others", user=claims["username"], revoked=revoked, ip=client_ip(request))
    return {"message": "Other sessions signed out", "revoked": revoked}


@router.delete("/sessions/{id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(id: int, request: Request):
    """
    End one of the caller's own sessions, this one included (which is a logout). Another user's
    session is 404: it is not theirs to see.
    """
    claims = _claims(request)
    session = use_cases.sessions.get(id)
    if session is None or session.user_id != claims["user_id"] or session.revoked_at is not None:
        raise NotFoundError("Session not found")
    use_cases.sessions.revoke(claims["user_id"], session.token_id)
    audit("session.revoke", user=claims["username"], session=id, ip=client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)

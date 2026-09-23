import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from starlette import status

from common.audit import audit
from config.settings import settings
from core.security.password import PasswordHasher
from infrastructure.mail import mailer
from interfaces.api.helpers.auth import CLAIMS_STATE_KEY, AuthHelper
from interfaces.api.helpers.cookies import clear_session_cookies, new_csrf_token, set_session_cookies
from interfaces.api.helpers.rate_limit import (
    account_lockout,
    client_ip,
    limit_login_attempts,
    limit_password_reset_attempts,
)
from interfaces.api.helpers.tenant import TOKEN_INVALID_STATE_KEY
from interfaces.api.schemas.auth import AuthLogin, PasswordForgot, PasswordReset
from wiring import api_use_cases

router = APIRouter(prefix="/auth", tags=["Auth"])
use_cases = api_use_cases()
logger = logging.getLogger(__name__)

# One answer whether or not the identifier exists, so the endpoint cannot be used to find out.
FORGOT_DETAIL = "If an account exists for that username or email, a password reset link has been sent."
RESET_INVALID_DETAIL = "This password reset link is invalid or has expired. Request a new one."


@router.post("/login", dependencies=[Depends(limit_login_attempts)])
def login(data: AuthLogin, request: Request):
    """
    Router for Login. Rate limited per client IP (API_LOGIN_RATE_LIMIT_PER_MINUTE) and locked per
    account after API_LOGIN_FAILURES_PER_ACCOUNT wrong passwords (helpers/rate_limit.py).

    Opens a server-side session (core/use_cases/user_session.py) and returns the token naming it.
    API clients get the token in the body and send it back as Authorization: Bearer. The web app
    sends use_cookie=true and gets the session as httpOnly cookies instead (helpers/cookies.py):
    the token is then never in a body JavaScript can read, which is the point.
    """
    account = data.username.strip().lower()
    ip = client_ip(request)
    try:
        account_lockout.check(account)
    except HTTPException:
        audit("login.locked", username=account, ip=ip)
        raise
    user = use_cases.users.authenticate_user(data.username, data.password)
    if not user or not user.is_active:
        account_lockout.record(account)
        audit("login.failure", username=account, ip=ip, reason="inactive" if user else "credentials")
        # 400 (not 401) on purpose: the web client treats 401 as "session expired".
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
    account_lockout.clear(account)
    if not user.farm_name:
        # Every row the API serves belongs to a farm; an account outside one has nothing to reach.
        audit("login.failure", username=account, ip=ip, reason="no_farm")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account is not assigned to a farm")
    channel = "cookie" if data.use_cookie else "header"
    access_token = AuthHelper.open_session(user, channel, request)
    audit("login.success", username=user.username, role=user.role, channel=channel, ip=ip)
    # One response shape for both channels: token is null when the session travels as a cookie.
    expires_in = AuthHelper.session_lifetime_seconds()
    if data.use_cookie:
        response = JSONResponse(content={"token": None, "token_type": "cookie", "expires_in": expires_in})
        set_session_cookies(response, access_token, new_csrf_token(), persistent=data.remember)
        return response
    return JSONResponse(content={"token": access_token, "token_type": "bearer", "expires_in": expires_in})


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request):
    """
    End the session: the row behind the token is revoked, so the token is refused from here on
    whichever channel carried it, and the browser cookies are cleared. Without a live session
    (already expired or signed out) it just clears the cookies.
    """
    claims = getattr(request.state, CLAIMS_STATE_KEY, None)
    if claims is not None:
        use_cases.sessions.revoke(claims["user_id"], claims["jti"])
        audit("logout", username=claims["username"], ip=client_ip(request))
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


@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_password_reset_attempts)],
)
def forgot_password(data: PasswordForgot, background: BackgroundTasks, request: Request):
    """
    Email a single-use, time-limited reset link to the account behind a username or email.

    Always 202 with the same body ({"message": ...}: "detail" is the error key). A different
    answer, or a slower one, would tell a caller
    which identifiers exist. The email goes out after the response for the same reason -
    sending takes measurably longer than not sending.
    """
    user = use_cases.users.find_by_identifier(data.identifier.strip())
    audit("password.forgot", identifier=data.identifier.strip()[:64], known=user is not None, ip=client_ip(request))
    if user is not None and user.is_active:
        token = AuthHelper.create_password_reset_token(user)
        link = f"{settings.API.WEB_BASE_URL.rstrip('/')}/reset-password?token={token}"
        background.add_task(
            mailer.send_password_reset,
            to=user.email,
            username=user.username,
            link=link,
            minutes=AuthHelper.RESET_TOKEN_MINUTES,
        )
    else:
        logger.info("Password reset requested for an unknown or inactive identifier")
    return {"message": FORGOT_DETAIL}


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(limit_password_reset_attempts)],
)
def reset_password(data: PasswordReset, request: Request):
    """
    Set a new password from a reset link. The token is single-use: it carries a fingerprint of
    the password it was issued against, so once the password changes it stops matching. Every
    session of the user is ended: a reset is what someone does when they suspect a stolen one.
    """
    try:
        claims = AuthHelper.decode_password_reset_token(data.token)
    except InvalidTokenError as e:
        audit("password.reset", outcome="invalid_token", ip=client_ip(request))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=RESET_INVALID_DETAIL) from e
    user = use_cases.users.get_own(int(claims["sub"]))
    if user is None or not user.is_active or claims.get("pfp") != PasswordHasher.fingerprint(user.password):
        audit("password.reset", outcome="stale_token", user_id=claims["sub"], ip=client_ip(request))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=RESET_INVALID_DETAIL)
    use_cases.users.set_password(user.id, data.new_password)
    audit("password.reset", outcome="success", user=user.username, ip=client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)

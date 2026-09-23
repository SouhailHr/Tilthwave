from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from starlette import status

from common.dates import parse_db_datetime
from config.settings import settings
from core.security.password import PasswordHasher
from interfaces.api.helpers.cookies import ACCESS_COOKIE
from interfaces.api.helpers.rate_limit import client_ip
from wiring import api_use_cases

# Pinned, not configured: a signing algorithm that can be changed from the environment can be
# weakened from the environment. Tokens are verified against this one algorithm and issuer only.
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "tilthwave"

# auto_error=False: a missing Authorization header is not an error by itself any more, the
# credential may be in the session cookie instead (see require_credential). Keeping the scheme
# object keeps the Authorize button and the bearer requirement in the OpenAPI docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

# Where TenantContextMiddleware stores the decoded claims so the request is decoded once.
CLAIMS_STATE_KEY = "auth_claims"


def require_credential(request: Request, bearer: str | None = Depends(oauth2_scheme)) -> str:
    """
    Dependency: the raw credential of the request, from the Authorization header (API clients:
    the simulator, curl, Burp) or the httpOnly session cookie (the web app). Neither present is
    the same JSON 401 as before. Verification is not done here: TenantContextMiddleware decoded
    the credential once already and the endpoint dependencies read its result from request.state.
    """
    token = bearer or request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


class AuthHelper:
    @classmethod
    def encode(cls, claims: dict, expires_at: datetime) -> str:
        """Sign `claims` with the pinned algorithm, issuer, issue time and the given expiry."""
        now = datetime.now(UTC)
        expires_at = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
        return jwt.encode(
            {**claims, "iss": JWT_ISSUER, "iat": now, "exp": expires_at},
            settings.API.SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )

    @classmethod
    def decode_token(cls, token: str) -> dict:
        """
        Decode and verify a token: signature, the pinned algorithm, issuer, issue time and expiry.
        @raises InvalidTokenError: expired, tampered, malformed, foreign or alien-algorithm token
        """
        return jwt.decode(
            token,
            settings.API.SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss"]},
        )

    # ---- session tokens ----------------------------------------------------------------------
    # A session token names a row of user_sessions in `jti`. TenantContextMiddleware refuses the
    # token when that row is missing, revoked, idle past API_SESSION_IDLE_MINUTES or past its
    # absolute end, so logout and "sign out everywhere" take effect at once.

    @classmethod
    def open_session(cls, user, channel: str, request: Request | None = None, remember: bool = True) -> str:
        """
        Open a server-side session for `user` and return the token that names it. `remember` (the
        sign-in form's "Keep me signed in") rides in the token as `rmb`, so a session re-issued later
        (a password change) keeps the same kind of cookie.
        """
        session = api_use_cases().sessions.open(
            user_id=user.id,
            channel=channel,
            user_agent=request.headers.get("user-agent") if request is not None else None,
            client_ip=client_ip(request) if request is not None else None,
        )
        claims = {
            "sub": str(user.id),
            "jti": session.token_id,
            "rmb": remember,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "farm_name": user.farm_name,  # tenant claim for per-farm object scoping
        }
        return cls.encode(claims, parse_db_datetime(session.expires_at))

    @classmethod
    def session_lifetime_seconds(cls) -> int:
        """What login reports as expires_in: the absolute lifetime (the idle limit ends it sooner)."""
        return settings.API.SESSION_MAX_HOURS * 3600

    # ---- password reset tokens -------------------------------------------------------------
    # Stateless: signed with the same key, but with a `purpose` claim (so it is never accepted as
    # a session token - the middleware rejects any token carrying one) and the password
    # fingerprint (so it is single-use: once the password changes, the fingerprint no longer
    # matches and the link is dead).

    RESET_PURPOSE = "password_reset"
    RESET_TOKEN_MINUTES = 30

    @classmethod
    def create_password_reset_token(cls, user) -> str:
        claims = {"sub": str(user.id), "purpose": cls.RESET_PURPOSE, "pfp": PasswordHasher.fingerprint(user.password)}
        return cls.encode(claims, datetime.now(UTC) + timedelta(minutes=cls.RESET_TOKEN_MINUTES))

    @classmethod
    def decode_password_reset_token(cls, token: str) -> dict:
        """@raises InvalidTokenError: expired, tampered, or not a password reset token"""
        claims = cls.decode_token(token)
        if claims.get("purpose") != cls.RESET_PURPOSE or "sub" not in claims:
            raise InvalidTokenError("not a password reset token")
        return claims

    @classmethod
    def _claims(cls, request: Request, token: str) -> dict:
        """Claims for the request: the middleware's copy when present, else a fresh decode."""
        claims = getattr(request.state, CLAIMS_STATE_KEY, None)
        if claims is not None:
            return claims
        try:
            return cls.decode_token(token)
        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
            ) from e

    @classmethod
    def get_current_user_username(cls, request: Request, token: str = Depends(require_credential)):
        """
        Dependency: the username of the authenticated caller (used as performed_by).
        """
        username = cls._claims(request, token).get("username")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        return username

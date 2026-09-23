from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from starlette import status

from config.settings import settings
from core.security.password import PasswordHasher
from interfaces.api.helpers.cookies import ACCESS_COOKIE

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
    def create_access_token(cls, data: dict) -> str:
        """
        Function to create access token
        @param data:
        @return: Encoded JWT
        """
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(minutes=settings.API.ACCESS_TOKEN_EXPIRE)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.API.SECRET_KEY, algorithm=settings.API.ALGORITHM)

    @classmethod
    def decode_token(cls, token: str) -> dict:
        """
        Decode and verify a token (signature, algorithm and expiry).
        @raises InvalidTokenError: expired, tampered or malformed token
        """
        return jwt.decode(token, settings.API.SECRET_KEY, algorithms=[settings.API.ALGORITHM])

    @classmethod
    def session_claims(cls, user) -> dict:
        """
        The claims a session token carries for `user`. `pfp` is a fingerprint of the password
        hash: TenantContextMiddleware rejects a token whose pfp no longer matches the row, so a
        password change signs every other session out (the changing session is re-issued).
        """
        return {
            "role": user.role,
            "username": user.username,
            "user_id": user.id,
            "user_full_name": f"{user.first_name} {user.last_name}",
            "farm_name": user.farm_name,  # tenant claim for per-farm object scoping
            "pfp": PasswordHasher.fingerprint(user.password),
        }

    # ---- password reset tokens -------------------------------------------------------------
    # Stateless: signed with the same key, but with a `purpose` claim (so it is never accepted as
    # a session token - the middleware rejects any token carrying one) and the password
    # fingerprint (so it is single-use: once the password changes, the fingerprint no longer
    # matches and the link is dead).

    RESET_PURPOSE = "password_reset"
    RESET_TOKEN_MINUTES = 30

    @classmethod
    def create_password_reset_token(cls, user) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=cls.RESET_TOKEN_MINUTES)
        claims = {
            "sub": str(user.id),
            "purpose": cls.RESET_PURPOSE,
            "pfp": PasswordHasher.fingerprint(user.password),
            "exp": expire,
        }
        return jwt.encode(claims, settings.API.SECRET_KEY, algorithm=settings.API.ALGORITHM)

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

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from starlette import status
from starlette.responses import JSONResponse

from config.settings import settings
from core.security.password import PasswordHasher

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Where TenantContextMiddleware stores the decoded claims so the request is decoded once.
CLAIMS_STATE_KEY = "auth_claims"


class AuthHelper:
    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        """
        Function to verify password
        @param plain_password:
        @param hashed_password:
        @return:
        """
        return PasswordHasher.verify(plain_password, hashed_password)

    @classmethod
    def get_password_hash(cls, password):
        """
        Function to hash a plain password
        @param password:
        @return: Hashed Password
        """
        return PasswordHasher.hash(password)

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
    def verify_access_token(cls, token: str) -> JSONResponse:
        """
        Function to verify access token and return a message indicating if the token is valid.

        @param token: JWT Token
        @return: A message stating if the token is valid or not.
        """
        try:
            cls.decode_token(token)
        except InvalidTokenError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from e
        return JSONResponse(status_code=status.HTTP_200_OK, content={"valid": True})

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
    def get_current_user(cls, request: Request, token: str = Depends(oauth2_scheme)):
        """
        Dependency: the raw bearer token of an authenticated caller.
        """
        if cls._claims(request, token).get("user_id") is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        return token

    @classmethod
    def get_current_user_username(cls, request: Request, token: str = Depends(oauth2_scheme)):
        """
        Dependency: the username of the authenticated caller (used as performed_by).
        """
        username = cls._claims(request, token).get("username")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        return username

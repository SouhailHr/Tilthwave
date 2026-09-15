from datetime import datetime, timedelta

from fastapi import HTTPException, Depends
from jose import jwt, JWTError
from passlib.context import CryptContext
from starlette import status
from starlette.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from config.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthHelper:

    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        """
        Function to verify password
        @param plain_password:
        @param hashed_password:
        @return:
        """
        return pwd_context.verify(plain_password, hashed_password)

    @classmethod
    def get_password_hash(cls, password):
        """
        Function to hash a plain password
        @param password:
        @return: Hashed Password
        """
        return pwd_context.hash(password)

    @classmethod
    def create_access_token(cls, data: dict):
        """
        Function to create access token
        @param data:
        @return: Encoded JWT
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.API.ACCESS_TOKEN_EXPIRE)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.API.SECRET_KEY, algorithm=settings.API.ALGORITHM)
        return encoded_jwt

    @classmethod
    def verify_access_token(cls, token: str) -> JSONResponse:
        """
        Function to verify access token and return a message indicating if the token is valid.

        @param token: JWT Token
        @return: A message stating if the token is valid or not.
        """
        try:
            # Attempt to decode the token using the same secret and algorithm used to create it
            payload = jwt.decode(token, settings.API.SECRET_KEY, algorithms=[settings.API.ALGORITHM])
            # Check token expire time
            expire = payload.get("exp")
            current_time = datetime.utcnow().timestamp()
            if expire <= current_time:
                return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=f"token has ben expired")
            return JSONResponse(status_code=status.HTTP_200_OK, content=f"token:{token}")
        except JWTError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail=f"Could not validate credentials. Error: {str(e)}")

    @classmethod
    def get_current_user(cls, token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, settings.API.SECRET_KEY, algorithms=[settings.API.ALGORITHM])
            user_id: int = payload.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        return token

    @classmethod
    def get_current_user_username(cls, token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, settings.API.SECRET_KEY, algorithms=[settings.API.ALGORITHM])
            username = payload.get("username")
            if not username:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
            return username
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

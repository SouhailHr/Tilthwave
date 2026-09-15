from pydantic import BaseModel


class AuthLogin(BaseModel):
    """
    Schema for Login , includes validation and serialization logic.
    """
    username: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "password": "securepassword",
            }
        }


class AuthVerifyToken(BaseModel):
    """
    Schema for Verify Token , includes validation and serialization logic.
    """
    token: str

    class Config:
        json_schema_extra = {
            "example": {
                "token": "put your token here please ",
            }
        }

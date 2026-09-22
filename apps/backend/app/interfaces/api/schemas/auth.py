from pydantic import BaseModel, ConfigDict, Field


class AuthLogin(BaseModel):
    """
    Schema for Login , includes validation and serialization logic.
    """

    username: str
    password: str
    use_cookie: bool = Field(
        default=False,
        description="Browser clients: keep the session in httpOnly cookies and omit the token from the body.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "password": "securepassword",
            }
        }
    )


class AuthVerifyToken(BaseModel):
    """
    Schema for Verify Token , includes validation and serialization logic.
    """

    token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "put your token here please ",
            }
        }
    )

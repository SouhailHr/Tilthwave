from pydantic import BaseModel, ConfigDict, Field, field_validator

from interfaces.api.schemas.users import password_fits_bcrypt


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
        extra="forbid",
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "password": "securepassword",
            }
        },
    )


class PasswordForgot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=1, max_length=256, description="Username or email address.")


class PasswordReset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, description="The token from the reset link.")
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def fits_bcrypt(cls, value: str) -> str:
        return password_fits_bcrypt(value)

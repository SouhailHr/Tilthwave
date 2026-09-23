from pydantic import BaseModel, ConfigDict, EmailStr, Field

from common import constants as global_constants
from core.security.password import MAX_PASSWORD_BYTES
from interfaces.api.schemas.base import IDENTIFIER_DOC


def password_fits_bcrypt(value: str | None) -> str | None:
    """bcrypt hashes at most 72 BYTES; a max_length in characters lets multibyte passwords through."""
    if value is not None and len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
    return value


class UserCreate(BaseModel):
    """
    Schema for creating a new user, includes validation and serialization logic.
    """

    username: str
    email: EmailStr
    phone_number: str = Field(description="Contact phone number of the user.")
    password: str | None = Field(
        default=None, exclude=True, description="Filled by the API with the hash; never accepted from clients."
    )
    text_password: str = Field(min_length=8, max_length=72, description="Plain password, hashed by the API.")
    first_name: str
    last_name: str
    role: str = Field(pattern=global_constants.USER_ROLES, description="User's role within the system.")
    is_active: bool = True
    # is_superuser is not accepted: it is derived from the role by the use case (extra="forbid" makes sending it a 422).
    farm_name: str | None = Field(description="The name of the farm managed by the user.", max_length=100)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "text_password": "securepassword",
                "first_name": "John",
                "last_name": "Doe",
                "role": "admin",
                "is_active": True,
                "farm_name": "Sunny Farms",
                "phone_number": "123-456-7890",
            }
        },
    )


class UserUpdate(BaseModel):
    """
    Schema for a partial user update (PATCH). Every field is optional; unknown fields are rejected.
    `farm_name` is deliberately absent: a user cannot be moved to another farm through the API.
    `is_superuser` is derived from `role` by the use case, never set directly.
    """

    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)
    farm_name: str | None = Field(default=None, exclude=True, description=IDENTIFIER_DOC)

    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, description="Contact phone number of the user.")
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)
    role: str | None = Field(
        default=None, pattern=global_constants.USER_ROLES, description="User's role within the system."
    )
    is_active: bool | None = None
    text_password: str | None = Field(
        default=None, min_length=8, max_length=72, description="New plain password, hashed by the API."
    )

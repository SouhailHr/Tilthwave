from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from interfaces.api.schemas.users import password_fits_bcrypt


class ProfileUpdate(BaseModel):
    """
    The fields a user may change on their own account. Role, farm and active flag are
    deliberately absent (extra="forbid" makes sending them a 422): those are an owner's to set,
    through PATCH /users/{id}. A new email needs the current password: reset links go there.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    current_password: str | None = Field(default=None, max_length=72, exclude=True)
    phone_number: str | None = Field(default=None, max_length=50)
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def fits_bcrypt(cls, value: str) -> str:
        return password_fits_bcrypt(value)

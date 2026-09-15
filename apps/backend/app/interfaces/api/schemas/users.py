from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from common import constants as global_constants


class UserCreate(BaseModel):
    """
    Schema for creating a new user, includes validation and serialization logic.
    """
    username: str
    email: EmailStr
    phone_number: str = Field(description="Contact phone number of the user.")
    password: Optional[str] = None
    text_password: str
    first_name: str
    last_name: str
    role: str = Field(pattern=global_constants.USER_ROLES, description="User's role within the system.")
    is_active: bool = True
    farm_name: Optional[str] = Field(description="The name of the farm managed by the user.", max_length=100)
    is_superuser: Optional[bool] = Field(default=False, description="Indicates if the user has superuser privileges.")

    @model_validator(mode="before")
    def set_superuser_status(cls, values):
        # Extract the role from the values dictionary
        role = values.get('role')
        # Determine if the user should be a superuser based on their role
        values['is_superuser'] = role in global_constants.SUPERUSER_ROLES
        return values

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "password": "securepassword",
                "first_name": "John",
                "last_name": "Doe",
                "role": "admin",
                "is_active": True,
                "farm_name": "Sunny Farms",
                "phone_number": "123-456-7890"
            }
        }

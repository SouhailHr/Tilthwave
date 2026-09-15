import dataclasses
from typing import Optional

from core.entities.base import BaseEntity


@dataclasses.dataclass
class Users(BaseEntity):
    """
    Users is an entity that represents a user, extending BaseEntity.
    Includes personal details, role, and account status.
    """

    username: str
    password: str
    email: str
    phone_number: str
    first_name: str
    last_name: str
    role: str
    is_active: bool = True
    is_superuser: bool = False
    farm_name: Optional[str] = None
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

    def to_dict(self):
        """Serialize without the password hash so it is never returned by the API."""
        data = super().to_dict()
        data.pop("password", None)
        return data

import dataclasses
from typing import ClassVar

from core.entities.base import BaseEntity


@dataclasses.dataclass
class Users(BaseEntity):
    """
    Users is an entity that represents a user, extending BaseEntity.
    Includes personal details, role, and account status.
    """

    # The password hash is persisted (to_dict) but never serialized for the API (to_public_dict).
    PRIVATE_FIELDS: ClassVar[tuple] = ("password",)

    username: str
    password: str
    email: str
    phone_number: str
    first_name: str
    last_name: str
    role: str
    is_active: bool = True
    is_superuser: bool = False
    farm_name: str | None = None
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

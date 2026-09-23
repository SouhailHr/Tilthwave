import dataclasses
from typing import ClassVar

from core.entities.base import BaseEntity


@dataclasses.dataclass
class UserSession(BaseEntity):
    """A signed-in session: the server-side half of a session token (see tables/user_session.py)."""

    # The jti is the credential's identity; the sessions list identifies rows by id instead.
    PRIVATE_FIELDS: ClassVar[tuple] = ("token_id",)

    token_id: str
    user_id: int
    channel: str
    expires_at: str
    last_seen: str = None
    revoked_at: str | None = None
    user_agent: str | None = None
    client_ip: str | None = None
    id: int = None
    updated_date: str = None
    created_date: str = None
    performed_by: str = None

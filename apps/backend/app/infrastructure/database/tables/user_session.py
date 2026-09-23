from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from common.dates import utc_now
from infrastructure.database.tables.base import TilthwaveBaseModel


class UserSession(TilthwaveBaseModel):
    """
    One signed-in session per login. The JWT carries the row's token_id as its `jti`; a token whose
    session is missing, revoked, idle past API_SESSION_IDLE_MINUTES or older than
    API_SESSION_MAX_HOURS is refused, however valid its signature. Logout revokes; a password
    change or reset, or deactivation, revokes every session of the user.
    """

    __tablename__ = "user_sessions"

    token_id = Column(String(64), unique=True, nullable=False, comment="The jti claim of the session's JWT.")
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="The signed-in user."
    )
    channel = Column(String(10), nullable=False, comment="How the credential travels: header (bearer) or cookie.")
    last_seen = Column(DateTime, nullable=False, default=utc_now, comment="Last request on this session (UTC).")
    expires_at = Column(DateTime, nullable=False, comment="Absolute end of the session (UTC), whatever the activity.")
    revoked_at = Column(DateTime, nullable=True, comment="Set by logout, a password change or an admin; ends it.")
    user_agent = Column(String(200), nullable=True, comment="User-Agent at login, for the sessions list.")
    client_ip = Column(String(45), nullable=True, comment="Client address at login, for the sessions list.")

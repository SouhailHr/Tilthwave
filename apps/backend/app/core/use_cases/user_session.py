"""
Server-side sessions behind the session tokens.

A login opens a row and the token carries its id as `jti`; every authenticated request resolves
the row and refuses the token when the row is gone, revoked, idle for longer than
API_SESSION_IDLE_MINUTES or older than API_SESSION_MAX_HOURS. That is what makes logout, "sign
out everywhere", a password change and deactivation take effect at once instead of when the
token happens to expire.
"""

import secrets
from datetime import datetime, timedelta

from common.dates import parse_db_datetime, utc_now
from config.settings import settings
from core.entities.user_session import UserSession as UserSessionEntity
from core.use_cases.base import BaseUseCase

# last_seen is written at most this often per session, so a busy dashboard is one UPDATE a
# minute rather than one per request.
TOUCH_INTERVAL_SECONDS = 60
# Ended sessions are kept this long for the record, then dropped at the user's next login.
PURGE_AFTER_DAYS = 30


class UserSessionUseCase(BaseUseCase):
    ENTITY = UserSessionEntity

    @staticmethod
    def idle_limit() -> timedelta:
        return timedelta(minutes=settings.API.SESSION_IDLE_MINUTES)

    @staticmethod
    def max_lifetime() -> timedelta:
        return timedelta(hours=settings.API.SESSION_MAX_HOURS)

    def open(self, user_id: int, channel: str, user_agent: str | None = None, client_ip: str | None = None):
        """A new live session for `user_id`; the caller puts its token_id in the JWT as `jti`."""
        now = utc_now()
        self.repo.purge(user_id, dead_before=now - timedelta(days=PURGE_AFTER_DAYS))
        entity = UserSessionEntity(
            token_id=secrets.token_urlsafe(32),
            user_id=user_id,
            channel=channel,
            last_seen=now,
            expires_at=now + self.max_lifetime(),
            user_agent=(user_agent or None) and user_agent[:200],
            client_ip=client_ip,
            performed_by=str(user_id),
        )
        return self.repo.create(entity)

    def is_live(self, session, now: datetime | None = None) -> bool:
        """Not revoked, not past its absolute end, not idle past the limit."""
        now = now or utc_now()
        if session.revoked_at is not None or parse_db_datetime(session.expires_at) <= now:
            return False
        return now - parse_db_datetime(session.last_seen) < self.idle_limit()

    def resolve(self, token_id: str | None):
        """
        The live session behind a token's `jti`, with its activity recorded, or None: the token
        must then be refused whatever its signature says.
        """
        if not token_id:
            return None
        session = self.repo.get_by_token_id(token_id)
        now = utc_now()
        if session is None or not self.is_live(session, now):
            return None
        if now - parse_db_datetime(session.last_seen) >= timedelta(seconds=TOUCH_INTERVAL_SECONDS):
            self.repo.touch(token_id, now)
        return session

    def revoke(self, user_id: int, token_id: str) -> int:
        """End one session of the user (logout, or "sign out that device")."""
        return self.repo.revoke(user_id, utc_now(), only_token_id=token_id)

    def revoke_all(self, user_id: int, except_token_id: str | None = None) -> int:
        """End every live session of the user, optionally sparing the one making the request."""
        return self.repo.revoke(user_id, utc_now(), except_token_id=except_token_id)

    def live_for(self, user_id: int):
        """The user's live sessions, newest first, for the sessions list."""
        now = utc_now()
        rows = self.repo.filter(
            [
                {"attribute": "user_id", "value": user_id, "condition": "eq"},
                {"attribute": "revoked_at", "value": None, "condition": "eq"},
            ],
            order_by="created_date",
            order_direction="desc",
        )
        return [row for row in rows if self.is_live(row, now)]

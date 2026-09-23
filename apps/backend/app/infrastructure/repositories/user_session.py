from datetime import datetime

from sqlalchemy import or_

from adapters.user_session import UserSessionAdaptor
from core.entities.user_session import UserSession as UserSessionEntity
from infrastructure.database.tables.user_session import UserSession
from infrastructure.repositories.base import BaseDBRepo


class UserSessionDBRepository(BaseDBRepo):
    """
    Sessions belong to a user, not a farm: unscoped. The callers (the auth middleware, the auth
    and account endpoints) only ever reach a row through its token_id or its verified user_id.
    """

    MODEL = UserSession
    ENTITY = UserSessionEntity
    ADAPTOR = UserSessionAdaptor
    TENANT_SCOPE = None

    def get_by_token_id(self, token_id: str):
        """The session a token names. token_id is a PRIVATE_FIELD (never filterable from the API),
        so this reads the column directly rather than through the filter DSL."""
        session = self.Session()
        try:
            obj = session.query(UserSession).filter(UserSession.token_id == token_id).one_or_none()
            return self.ADAPTOR.model_to_entity(obj=obj) if obj else None
        except Exception as e:
            raise self._translate("fetching", e) from e
        finally:
            session.close()

    def touch(self, token_id: str, now: datetime) -> None:
        """Record activity on a session: one UPDATE, no read."""
        session = self.Session()
        try:
            session.query(UserSession).filter(UserSession.token_id == token_id).update({"last_seen": now})
            session.commit()
        except Exception as e:
            session.rollback()
            raise self._translate("touching", e) from e
        finally:
            session.close()

    def revoke(self, user_id: int, now: datetime, only_token_id: str | None = None, except_token_id: str | None = None):
        """
        End the live sessions of `user_id`: all of them, one (`only_token_id`) or all but one
        (`except_token_id`). Already-revoked rows keep their original revoked_at.
        @return: number of sessions revoked
        """
        session = self.Session()
        try:
            query = session.query(UserSession).filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            if only_token_id is not None:
                query = query.filter(UserSession.token_id == only_token_id)
            if except_token_id is not None:
                query = query.filter(UserSession.token_id != except_token_id)
            count = query.update({"revoked_at": now}, synchronize_session=False)
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            raise self._translate("revoking", e) from e
        finally:
            session.close()

    def purge(self, user_id: int, dead_before: datetime) -> int:
        """Delete the user's sessions that ended (expired or revoked) before `dead_before`."""
        session = self.Session()
        try:
            query = session.query(UserSession).filter(
                UserSession.user_id == user_id,
                or_(UserSession.expires_at < dead_before, UserSession.revoked_at < dead_before),
            )
            count = query.delete(synchronize_session=False)
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            raise self._translate("purging", e) from e
        finally:
            session.close()

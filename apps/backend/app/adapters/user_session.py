from adapters.base import BaseAdaptor
from common.dates import iso_utc
from core.entities.user_session import UserSession as UserSessionEntity


class UserSessionAdaptor(BaseAdaptor):
    ENTITY = UserSessionEntity
    CUSTOM_MAPPER = {
        "last_seen": {"field_in_model": "last_seen", "convert_to": iso_utc},
        "expires_at": {"field_in_model": "expires_at", "convert_to": iso_utc},
        "revoked_at": {"field_in_model": "revoked_at", "convert_to": iso_utc},
    }

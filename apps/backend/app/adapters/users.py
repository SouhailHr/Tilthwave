from adapters.base import BaseAdaptor
from core.entities.users import Users as UserEntity


class UserAdaptor(BaseAdaptor):
    ENTITY = UserEntity

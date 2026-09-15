from adapters.users import UserAdaptor
from core.entities.users import Users as UserEntity
from infrastructure.database.tables.users import Users
from infrastructure.repositories.base import BaseDBRepo


class UserDBRepository(BaseDBRepo):
    """
    UserRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """

    MODEL = Users
    ENTITY = UserEntity
    ADAPTOR = UserAdaptor
    TENANT_SCOPE = ("column", "farm_name")

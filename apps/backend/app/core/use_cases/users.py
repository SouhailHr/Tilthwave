import logging

from common import constants as global_constants
from common.tenant_context import without_tenant
from core.entities.users import Users as UserEntity
from core.security.password import PasswordHasher
from core.use_cases.base import BaseUseCase
from core.use_cases.exceptions import UseCaseException

logger = logging.getLogger(__name__)

# Verified against when the username does not exist, so a login attempt costs one bcrypt check
# either way and response time does not reveal which usernames are taken.
_UNKNOWN_USER_HASH = PasswordHasher.hash("not-a-real-password")


class UserUseCase(BaseUseCase):
    ENTITY = UserEntity

    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        """
        Verify a plaintext password against the hashed password.

        @param plain_password: The plaintext password to verify.
        @param  hashed_password: The hashed password from the database.
        @return: True if the password is correct, False otherwise.
        """
        return PasswordHasher.verify(plain_password, hashed_password)

    @staticmethod
    def is_superuser_role(role: str) -> bool:
        """The one rule deriving the superuser flag from a role."""
        return role in global_constants.SUPERUSER_ROLES

    def create(self, entity: ENTITY):
        """
        Create a user; is_superuser is always derived from the role, never taken from the caller.
        """
        entity.is_superuser = self.is_superuser_role(entity.role)
        return self.repo.create(entity)

    def authenticate_user(self, username: str, password: str):
        """
        Authenticate a user based on username and password.

        @param username: The username of the user trying to authenticate.
        @param password: The password provided for authentication.
        @return: The User entity if authentication is successful, None otherwise.
        """
        filters = [{"attribute": "username", "value": username, "condition": "eq"}]
        users = self.repo.filter(filters)

        # Assuming the filter returns a list of users, we take the first one if it exists
        user = users[0] if users else None

        if user is None:
            self.verify_password(password, _UNKNOWN_USER_HASH)  # same cost as a real check
            return None
        if self.verify_password(password, user.password):
            return user
        return None

    def update(self, id: int, data: dict):
        """
        Update an entity by ID using the repository.
        1- check if role is in the data and it is a valid role
        2- if yes put conditions to update is_superuser
        3- if user role is in admin or owner set the is_superuser to true

        @param id: ID of the entity to update.
        @param data: Dictionary of data to update.
        @return: The updated entity.
        """
        # Check if 'role' is provided in the data
        role = data.get("role")

        if role:
            # Validate the provided role
            if role not in global_constants.USER_ROLES_LIST:
                raise UseCaseException(
                    class_name=self.__class__.__name__,
                    message=f"user role must be one of the following {global_constants.USER_ROLES_LIST}",
                )

            # Set 'is_superuser' based on whether the role is a superuser role
            data["is_superuser"] = self.is_superuser_role(role)

        # Proceed with the update, whether 'role' was included or not
        return self.repo.update(id, data)

    def get_users_by_role(self, role: str):
        """
         This method gets all users with a specific role
        @param role:
        @return: list of users
        """
        filters = [{"attribute": "role", "value": role, "condition": "eq"}]
        users = self.filter(filters=filters)

        return users

    def find_by_identifier(self, identifier: str):
        """The user whose username or email is exactly `identifier`, or None."""
        for attribute in ("username", "email"):
            user = self.repo.first([{"attribute": attribute, "value": identifier, "condition": "eq"}])
            if user is not None:
                return user
        return None

    # ---- the caller's own account ---------------------------------------------------------
    # These take the user_id straight from the verified session and run outside the farm
    # filter (see common.tenant_context.without_tenant): the row is the caller's by
    # construction, and a farm-less bootstrap admin must still be able to see and edit itself.

    def get_own(self, user_id: int):
        with without_tenant():
            return self.repo.get(user_id)

    def update_own_profile(self, user_id: int, data: dict):
        with without_tenant():
            return self.repo.update(user_id, data)

    def set_password(self, user_id: int, new_password: str):
        with without_tenant():
            return self.repo.update(user_id, {"password": PasswordHasher.hash(new_password)})

    def change_password(self, user_id: int, current_password: str, new_password: str):
        """
        Self-service password change: the current password must verify first.
        @raises UseCaseException: wrong current password (one bcrypt check either way)
        """
        user = self.get_own(user_id)
        if user is None or not self.verify_password(current_password, user.password):
            raise UseCaseException(class_name=self.__class__.__name__, message="Current password is incorrect")
        return self.set_password(user_id, new_password)

    def get_stats(self):
        """
        this method gets the users stats
        @return:
         stats_dict = {
           "total_users": 5,
           "total_superusers": { Owners : 2 , Admins : 1}
           "total_workers": 5,
           "total_engineers": 5,
         }

        """

        total_users = self.filter()
        total_owners = self.get_users_by_role(role="owner")
        total_admins = self.get_users_by_role(role="admin")
        total_workers = self.get_users_by_role(role="worker")
        total_engineers = self.get_users_by_role(role="engineer")

        if total_owners is None:
            total_owners = 0
        if total_admins is None:
            total_admins = 0
        if total_workers is None:
            total_workers = 0
        if total_engineers is None:
            total_engineers = 0

        stats_dict = {
            "total_users": len(total_users),
            "total_owners": len(total_owners),
            "total_admins": len(total_admins),
            "total_workers": len(total_workers),
            "total_engineers": len(total_engineers),
        }
        return stats_dict

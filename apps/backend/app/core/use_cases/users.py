import logging

from common import constants as global_constants
from common.audit import audit
from common.exceptions import ForbiddenError
from common.tenant_context import get_current_tenant, without_tenant
from core.entities.users import Users as UserEntity
from core.security.password import PasswordHasher
from core.use_cases.base import BaseUseCase
from core.use_cases.exceptions import UseCaseException

logger = logging.getLogger(__name__)

# Verified against when the username does not exist, so a login attempt costs one bcrypt check
# either way and response time does not reveal which usernames are taken.
_UNKNOWN_USER_HASH = PasswordHasher.hash("not-a-real-password")

# What a user may not do to their own row through /users: those go through an owner (role,
# status) or through /account (password), where the current password is required.
_OWN_ROW_FIELDS = ("role", "is_active", "password")


class UserUseCase(BaseUseCase):
    """
    Users of a farm, and the rules on who may change whom (the actor is the request's tenant
    context; scripts and the seed have none and are unrestricted):

    - only an owner may create an admin or owner, give or take one of those roles, or change,
      deactivate, delete or set the password of a user holding one; an admin manages workers and
      engineers;
    - nobody changes their own role, status or password through /users, nor deletes themselves;
    - the last active owner of a farm cannot be demoted, deactivated or deleted: without an owner
      nobody could appoint an admin again.
    """

    ENTITY = UserEntity

    def __init__(self, repo, sessions):
        """
        @param sessions: UserSessionUseCase; deactivating or deleting a user ends their sessions, and
        a password change or reset ends every session but the one that made the change.
        """
        super().__init__(repo)
        self.sessions = sessions

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

    # ---- who may do what -------------------------------------------------------------------

    @staticmethod
    def _actor():
        """The caller, or None outside a request (scripts, seed): then nothing is restricted."""
        return get_current_tenant()

    @staticmethod
    def _require_owner_for(actor, role: str, what: str) -> None:
        if (
            actor is not None
            and role in global_constants.SUPERUSER_ROLES
            and actor.get("role") != global_constants.OWNER_ROLE
        ):
            raise ForbiddenError(f"Only an owner can {what} an admin or owner")

    def _active_owners(self, farm_name: str) -> int:
        return self.repo.count(
            [
                {"attribute": "farm_name", "value": farm_name, "condition": "eq"},
                {"attribute": "role", "value": global_constants.OWNER_ROLE, "condition": "eq"},
                {"attribute": "is_active", "value": True, "condition": "eq"},
            ]
        )

    def _guard_last_owner(self, target, what: str) -> None:
        if (
            target.role == global_constants.OWNER_ROLE
            and target.is_active
            and self._active_owners(target.farm_name) <= 1
        ):
            raise UseCaseException(
                class_name=self.__class__.__name__,
                message=f"{target.username} is the last active owner of {target.farm_name} and cannot be {what}",
            )

    # ---- CRUD --------------------------------------------------------------------------------

    def create(self, entity: ENTITY):
        """
        Create a user; is_superuser is always derived from the role, never taken from the caller.
        """
        actor = self._actor()
        self._require_owner_for(actor, entity.role, "create")
        entity.is_superuser = self.is_superuser_role(entity.role)
        created = self.repo.create(entity)
        audit("user.create", actor=actor and actor.get("username"), user=created.username, role=created.role)
        return created

    def authenticate_user(self, username: str, password: str):
        """
        Authenticate a user based on username and password.

        @param username: The username of the user trying to authenticate.
        @param password: The password provided for authentication.
        @return: The User entity if authentication is successful, None otherwise.
        """
        user = self.repo.first([{"attribute": "username", "value": username, "condition": "eq"}])
        if user is None:
            self.verify_password(password, _UNKNOWN_USER_HASH)  # same cost as a real check
            return None
        if self.verify_password(password, user.password):
            return user
        return None

    def update(self, id: int, data: dict):
        """
        Update a user, under the rules in the class docstring. A role change re-derives
        is_superuser; a deactivation or a password set by an admin ends the user's sessions.

        @return: The updated entity, or None when the row is missing or outside the caller's farm.
        """
        role = data.get("role")
        if role and role not in global_constants.USER_ROLES_LIST:
            raise UseCaseException(
                class_name=self.__class__.__name__,
                message=f"user role must be one of the following {global_constants.USER_ROLES_LIST}",
            )
        target = self.repo.get(id)
        if target is None:
            return None
        actor = self._actor()
        if actor is not None and actor.get("user_id") == target.id:
            own = [field for field in _OWN_ROW_FIELDS if field in data]
            if own:
                raise UseCaseException(
                    class_name=self.__class__.__name__,
                    message="Your own role and status are an owner's to change; your password changes in Settings",
                )
        self._require_owner_for(actor, target.role, "change")
        if role and role != target.role:
            self._require_owner_for(actor, role, "appoint")
        if (role and role != target.role) or data.get("is_active") is False:
            self._guard_last_owner(target, "demoted or deactivated")
        if role:
            data["is_superuser"] = self.is_superuser_role(role)

        updated = self.repo.update(id, data)
        if updated is None:
            return None
        who = actor and actor.get("username")
        if role and role != target.role:
            audit("user.role_change", actor=who, user=target.username, old=target.role, new=role)
        if "is_active" in data and data["is_active"] != target.is_active:
            audit("user.activate" if data["is_active"] else "user.deactivate", actor=who, user=target.username)
        if "password" in data:
            audit("user.password_set", actor=who, user=target.username)
        if data.get("is_active") is False or "password" in data:
            # A deactivated account is refused on its next request anyway (the middleware reloads the
            # row); ending the sessions makes the sessions list say so too. A password set by an
            # admin signs the user out everywhere, as their own change would.
            self.sessions.revoke_all(id)
        return updated

    def delete(self, id: int):
        target = self.repo.get(id)
        if target is None:
            return False
        actor = self._actor()
        if actor is not None and actor.get("user_id") == target.id:
            raise UseCaseException(class_name=self.__class__.__name__, message="You cannot delete your own account")
        self._require_owner_for(actor, target.role, "delete")
        self._guard_last_owner(target, "deleted")
        self.sessions.revoke_all(id)
        deleted = self.repo.delete(id)
        if deleted:
            audit("user.delete", actor=actor and actor.get("username"), user=target.username, role=target.role)
        return deleted

    def find_by_identifier(self, identifier: str):
        """The user whose username or email is exactly `identifier`, or None."""
        for attribute in ("username", "email"):
            user = self.repo.first([{"attribute": attribute, "value": identifier, "condition": "eq"}])
            if user is not None:
                return user
        return None

    # ---- the caller's own account ---------------------------------------------------------
    # These take the user_id straight from the verified session and run outside the farm
    # filter (see common.tenant_context.without_tenant): the row is the caller's by construction.

    def get_own(self, user_id: int):
        with without_tenant():
            return self.repo.get(user_id)

    def update_own_profile(self, user_id: int, data: dict, current_password: str | None = None):
        """
        Contact details. Changing the email re-authenticates: it is where reset links go, so a
        hijacked session must not be able to point it elsewhere.
        @raises UseCaseException: the email changes and the current password is missing or wrong
        """
        user = self.get_own(user_id)
        if user is None:
            return None
        new_email = data.get("email")
        if new_email is not None and new_email != user.email:
            if not current_password or not self.verify_password(current_password, user.password):
                raise UseCaseException(
                    class_name=self.__class__.__name__, message="Current password is required to change the email"
                )
            audit("account.email_change", user=user.username, old=user.email, new=new_email)
        with without_tenant():
            return self.repo.update(user_id, data)

    def set_password(self, user_id: int, new_password: str, keep_token_id: str | None = None):
        """Store a new password and end every session of the user, except `keep_token_id`."""
        with without_tenant():
            user = self.repo.update(user_id, {"password": PasswordHasher.hash(new_password)})
        self.sessions.revoke_all(user_id, except_token_id=keep_token_id)
        return user

    def change_password(self, user_id: int, current_password: str, new_password: str):
        """
        Self-service password change: the current password must verify first.
        @raises UseCaseException: wrong current password (one bcrypt check either way)
        """
        user = self.get_own(user_id)
        if user is None or not self.verify_password(current_password, user.password):
            raise UseCaseException(class_name=self.__class__.__name__, message="Current password is incorrect")
        return self.set_password(user_id, new_password)

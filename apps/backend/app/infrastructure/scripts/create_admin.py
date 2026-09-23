"""
Bootstrap the farm's owner account.

Reads each field from ADMIN_* environment variables; prompts interactively for anything missing.
Password is read with getpass when prompted so it is not echoed. The account gets the `owner`
role: only an owner can appoint admins (core/use_cases/users.py), so the first account must be
one. A farm is required (every account belongs to one) and is created, bare, when it does not
exist yet. `bootstrap_admin` is also what the seed script uses, so there is a single definition
of "the first account".

Usage (inside the api container):
    python /backend/app/infrastructure/scripts/create_admin.py
    ADMIN_USERNAME=admin ADMIN_PASSWORD=... python /backend/app/infrastructure/scripts/create_admin.py

From the host:
    make create-admin
"""

import getpass
import os
import sys

from adapters.farm import FarmAdaptor
from adapters.users import UserAdaptor
from core.security.password import PasswordHasher
from wiring import api_use_cases, repositories

BOOTSTRAP_ROLE = "owner"


def ensure_farm(farm_name: str, performed_by: str) -> None:
    """Create `farm_name` with placeholder details when it does not exist; the owner fills them in."""
    farm_repo = repositories().farm
    if farm_repo.first([{"attribute": "farm_name", "value": farm_name, "condition": "eq"}]) is None:
        farm_repo.create(
            FarmAdaptor.dict_to_entity(
                {"farm_name": farm_name, "address": "", "location": None, "size": 0.0, "performed_by": performed_by}
            )
        )


def bootstrap_admin(
    username: str,
    password: str,
    farm_name: str,
    email=None,
    first_name="Admin",
    last_name="User",
    phone_number="+0000000000",
    performed_by="bootstrap",
):
    """
    Create the active owner of `farm_name` through the users use case, creating the farm if needed.

    @return: the created user entity
    @raises ValueError: empty password or farm name
    """
    if not password:
        raise ValueError("Password is required")
    if not farm_name:
        raise ValueError("Farm name is required: every account belongs to a farm")
    ensure_farm(farm_name, performed_by)
    entity = UserAdaptor.dict_to_entity(
        {
            "username": username,
            "email": email or f"{username}@example.com",
            "password": PasswordHasher.hash(password),
            "phone_number": phone_number,
            "first_name": first_name,
            "last_name": last_name,
            "role": BOOTSTRAP_ROLE,
            "is_active": True,
            "is_superuser": True,
            "farm_name": farm_name,
            "performed_by": performed_by,
        }
    )
    return api_use_cases().users.create(entity)


def _prompt(label: str, env_key: str, default: str | None = None, secret: bool = False) -> str:
    value = os.environ.get(env_key)
    if value:
        return value
    if secret:
        return getpass.getpass(f"{label}: ")
    suffix = f" [{default}]" if default else ""
    entered = input(f"{label}{suffix}: ").strip()
    return entered or (default or "")


def main() -> None:
    username = _prompt("Username", "ADMIN_USERNAME", default="admin")
    email = _prompt("Email", "ADMIN_EMAIL", default=f"{username}@example.com")
    first_name = _prompt("First name", "ADMIN_FIRST_NAME", default="Admin")
    last_name = _prompt("Last name", "ADMIN_LAST_NAME", default="User")
    phone_number = _prompt("Phone", "ADMIN_PHONE", default="+0000000000")
    farm_name = _prompt("Farm name", "ADMIN_FARM_NAME")
    if not farm_name:
        sys.exit("Farm name is required: every account belongs to a farm")
    password = _prompt("Password", "ADMIN_PASSWORD", secret=True)
    if not password:
        sys.exit("Password is required")

    created = bootstrap_admin(
        username,
        password,
        farm_name=farm_name,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
    )
    print(f"Created owner id={created.id} username={created.username} farm={created.farm_name}")


if __name__ == "__main__":
    main()

"""
Bootstrap an admin user.

Reads each field from ADMIN_* environment variables; prompts interactively for
anything missing. Password is read with getpass when prompted so it is not
echoed. `bootstrap_admin` is also what the seed script uses, so there is a single
definition of "an admin user".

Usage (inside the api container):
    python /backend/app/infrastructure/scripts/create_admin.py
    ADMIN_USERNAME=admin ADMIN_PASSWORD=... python /backend/app/infrastructure/scripts/create_admin.py

From the host:
    make create-admin
"""

import getpass
import os
import sys

from adapters.users import UserAdaptor
from core.security.password import PasswordHasher
from wiring import api_use_cases


def bootstrap_admin(
    username: str,
    password: str,
    farm_name=None,
    email=None,
    first_name="Admin",
    last_name="User",
    phone_number="+0000000000",
    performed_by="bootstrap",
):
    """
    Create an active superuser with the admin role through the users use case.

    @return: the created user entity
    @raises ValueError: empty password
    """
    if not password:
        raise ValueError("Password is required")
    entity = UserAdaptor.dict_to_entity(
        {
            "username": username,
            "email": email or f"{username}@example.com",
            "password": PasswordHasher.hash(password),
            "phone_number": phone_number,
            "first_name": first_name,
            "last_name": last_name,
            "role": "admin",
            "is_active": True,
            "is_superuser": True,
            "farm_name": farm_name or None,
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
    farm_name = _prompt("Farm name (blank for none)", "ADMIN_FARM_NAME", default="")
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
    print(f"Created admin user id={created.id} username={created.username}")


if __name__ == "__main__":
    main()

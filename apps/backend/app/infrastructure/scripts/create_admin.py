"""
Bootstrap an admin user.

Reads each field from ADMIN_* environment variables; prompts interactively for
anything missing. Password is read with getpass when prompted so it is not
echoed.

Usage (inside the api container):
    python /fwc/app/infrastructure/scripts/create_admin.py
    ADMIN_USERNAME=admin ADMIN_PASSWORD=... python /fwc/app/infrastructure/scripts/create_admin.py

From the host:
    make create-admin
"""
import getpass
import os
import sys

from adapters.users import UserAdaptor
from config.settings import settings
from core.use_cases.users import UserUseCase
from infrastructure.repositories.users import UserDBRepository
from interfaces.api.helpers.auth import AuthHelper


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
    repo = UserDBRepository(uri=settings.DATABASE.URI)
    use_case = UserUseCase(repo=repo)

    username = _prompt("Username", "ADMIN_USERNAME", default="admin")
    email = _prompt("Email", "ADMIN_EMAIL", default=f"{username}@example.com")
    first_name = _prompt("First name", "ADMIN_FIRST_NAME", default="Admin")
    last_name = _prompt("Last name", "ADMIN_LAST_NAME", default="User")
    phone_number = _prompt("Phone", "ADMIN_PHONE", default="+0000000000")
    farm_name = _prompt("Farm name (blank for none)", "ADMIN_FARM_NAME", default="")
    password = _prompt("Password", "ADMIN_PASSWORD", secret=True)
    if not password:
        sys.exit("Password is required")

    data = {
        "username": username,
        "email": email,
        "password": AuthHelper.get_password_hash(password),
        "phone_number": phone_number,
        "first_name": first_name,
        "last_name": last_name,
        "role": "admin",
        "is_active": True,
        "is_superuser": True,
        "farm_name": farm_name or None,
        "performed_by": "bootstrap",
    }
    entity = UserAdaptor.dict_to_entity(data)
    created = use_case.create(entity)
    print(f"Created admin user id={created.id} username={created.username}")


if __name__ == "__main__":
    main()
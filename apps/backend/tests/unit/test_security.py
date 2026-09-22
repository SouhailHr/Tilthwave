import pytest
from pydantic import ValidationError

from config.settings import APISettings, reject_placeholder
from core.security.password import PasswordHasher
from interfaces.api.helpers.permission import has_permission, translate_method_to_action

GOOD_KEY = "k7Zq2vXm9pL4nR8tW1yB6cD3fG5hJ0aE2sU4iO7rT9wQ1eY3"


def test_password_roundtrip_and_mismatch():
    hashed = PasswordHasher.hash("correct horse")
    assert hashed.startswith("$2b$")
    assert PasswordHasher.verify("correct horse", hashed)
    assert not PasswordHasher.verify("wrong", hashed)
    assert not PasswordHasher.verify("", hashed)
    assert not PasswordHasher.verify("x", "not-a-hash")


def test_password_longer_than_bcrypt_limit_is_rejected():
    with pytest.raises(ValueError):
        PasswordHasher.hash("a" * 73)


@pytest.mark.parametrize(
    "value",
    [
        "change-me-to-a-long-random-secret-value",
        "short",
        "my-super-secret-key-1234567890abcdef",
    ],
)
def test_placeholder_or_short_secret_key_is_rejected(value):
    with pytest.raises(ValueError):
        reject_placeholder("API_SECRET_KEY", value, 32)
    with pytest.raises(ValidationError):
        APISettings(SECRET_KEY=value, _env_file=None)


def test_real_secret_key_is_accepted():
    assert APISettings(SECRET_KEY=GOOD_KEY, _env_file=None).SECRET_KEY == GOOD_KEY


@pytest.mark.parametrize(
    "method,action",
    [
        ("GET", "read"),
        ("HEAD", "read"),
        ("OPTIONS", "read"),
        ("POST", "write"),
        ("PUT", "update"),
        ("PATCH", "update"),
        ("DELETE", "delete"),
        ("TRACE", "deny"),
        ("purge", "deny"),
    ],
)
def test_method_to_action(method, action):
    assert translate_method_to_action(method) == action


@pytest.mark.parametrize(
    "role,resource,action,allowed",
    [
        ("admin", "users", "delete", True),
        ("owner", "sensor-records", "write", False),  # nobody may write records through the API
        ("worker", "zones", "update", False),  # the former PATCH->read escalation
        ("worker", "trees", "update", True),
        ("engineer", "users", "read", False),
        ("engineer", "users", "write", False),
        ("worker", "unknown-resource", "read", False),
        ("ghost", "users", "read", False),
        ("admin", "zones", "deny", False),
    ],
)
def test_rbac_matrix(role, resource, action, allowed):
    assert has_permission(role, resource, action) is allowed

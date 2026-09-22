"""
Test bootstrap.

The settings module reads the environment at import time, so the environment is prepared
here, before any application module is imported. The whole graph (wiring.repositories()) then
runs against a throwaway SQLite file: no Postgres, no broker, a few hundred milliseconds.
"""

import os
import shutil
import tempfile

import pytest

_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="tilthwave-tests-"), "tilthwave.db")

os.environ.update(
    {
        "POSTGRES_URI": f"sqlite:///{_TMP_DB}",
        "POSTGRES_HOST": "unused",
        "POSTGRES_USER": "unused",
        "POSTGRES_PASSWORD": "unused",
        "POSTGRES_DB": "unused",
        "API_SECRET_KEY": "k7Zq2vXm9pL4nR8tW1yB6cD3fG5hJ0aE2sU4iO7rT9wQ1eY3",
        "API_ALGORITHM": "HS256",
        "API_ACCESS_TOKEN_EXPIRE": "60",
        "STREAMER_BROKER_HOSTS": '["broker:9092"]',
        "STREAMER_SENSORS_TOPIC": "test.sensors",
        "STREAMER_WATER_CONTROL_TOPIC": "test.water-control",
        "FLOW_RUNNER_MINUTES": "1",
        "FLOW_RUNNER_MAX_IRRIGATION_MINUTES": "60",
        "FLOW_RUNNER_MAX_READING_AGE_MINUTES": "30",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "Adm1n-Test-Passw0rd!",
        "LOG_LEVEL": "WARNING",
    }
)

from config.settings import settings  # noqa: E402  (environment must be set first)
from infrastructure.database.base import Base  # noqa: E402
from infrastructure.repositories.base import BaseDBRepo  # noqa: E402

FARM_A = "Sunny Farms"
FARM_B = "Shady Acres"


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    engine = BaseDBRepo.get_engine(settings.DATABASE.URI)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    shutil.rmtree(os.path.dirname(_TMP_DB), ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_tables():
    """Every test starts from empty tables (schema kept) and an empty login rate-limit window."""
    from interfaces.api.helpers.rate_limit import login_rate_limiter, password_reset_rate_limiter

    login_rate_limiter.reset()
    password_reset_rate_limiter.reset()
    yield
    engine = BaseDBRepo.get_engine(settings.DATABASE.URI)
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def repos():
    from wiring import repositories

    return repositories()


@pytest.fixture
def use_cases():
    from wiring import api_use_cases

    return api_use_cases()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from interfaces.api.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def make_farm(repos):
    from adapters.farm import FarmAdaptor

    def _make(farm_name=FARM_A):
        return repos.farm.create(
            FarmAdaptor.dict_to_entity(
                {
                    "farm_name": farm_name,
                    "address": "1 Olive Lane",
                    "location": {"lat": 0, "lon": 0},
                    "size": 10.0,
                    "performed_by": "tests",
                }
            )
        )

    return _make


@pytest.fixture
def make_user(repos):
    from adapters.users import UserAdaptor
    from core.security.password import PasswordHasher

    def _make(username, role="admin", farm_name=FARM_A, password="Passw0rd-Test!"):
        return repos.users.create(
            UserAdaptor.dict_to_entity(
                {
                    "username": username,
                    "email": f"{username}@example.com",
                    "phone_number": "+000",
                    "password": PasswordHasher.hash(password),
                    "first_name": username.title(),
                    "last_name": "User",
                    "role": role,
                    "is_active": True,
                    "is_superuser": role in ("admin", "owner"),
                    "farm_name": farm_name,
                    "performed_by": "tests",
                }
            )
        )

    return _make


@pytest.fixture
def token_for(repos, make_user):
    """
    A signed token for a user that exists in the database (created on demand, or aligned to the
    requested role/farm when it already exists): the middleware validates the row on every request.
    Pass user_id to mint a token for a row that does not exist.
    """
    from interfaces.api.helpers.auth import AuthHelper

    def _token(username="admin", role="admin", farm_name=FARM_A, user_id=None):
        if user_id is None:
            user = repos.users.first([{"attribute": "username", "value": username, "condition": "eq"}])
            if user is None:
                user = make_user(username, role=role, farm_name=farm_name)
            elif user.role != role or user.farm_name != farm_name:
                user = repos.users.update(user.id, {"role": role, "farm_name": farm_name})
            user_id = user.id
        return AuthHelper.create_access_token(
            {"role": role, "username": username, "user_id": user_id, "user_full_name": username, "farm_name": farm_name}
        )

    return _token


@pytest.fixture
def auth_headers(token_for):
    def _headers(**claims):
        return {"Authorization": f"Bearer {token_for(**claims)}"}

    return _headers


@pytest.fixture
def make_zone(repos):
    from adapters.zone import ZoneAdaptor

    def _make(zone_name="Zone A", farm_name=FARM_A, **triggers):
        data = {
            "farm_name": farm_name,
            "zone_name": zone_name,
            "size": 100,
            "location": {},
            "soil_type": "Loamy",
            "moisture_trigger_start": 50,
            "moisture_trigger_stop": 80,
            "saturation_trigger_start": 60,
            "saturation_trigger_stop": 90,
            "performed_by": "tests",
        }
        data.update(triggers)
        return repos.zone.create(ZoneAdaptor.dict_to_entity(data))

    return _make


def zone_payload(zone_name="Zone New", farm_name=FARM_A, **overrides):
    """A valid POST /zones body (the shape the web create form sends)."""
    payload = {
        "farm_name": farm_name,
        "zone_name": zone_name,
        "size": 10,
        "soil_type": "Loamy",
        "moisture_trigger_start": 50,
        "moisture_trigger_stop": 80,
        "saturation_trigger_start": 60,
        "saturation_trigger_stop": 90,
    }
    payload.update(overrides)
    return payload


def backdate(repo, model, row_id: int, minutes: int) -> None:
    """Move a row's created_date into the past (UTC, like the column default)."""
    from datetime import timedelta

    from common.dates import utc_now

    with repo.Session() as session:
        session.get(model, row_id).created_date = utc_now() - timedelta(minutes=minutes)
        session.commit()

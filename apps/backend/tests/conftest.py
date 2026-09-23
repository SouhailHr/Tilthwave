"""
Test bootstrap.

The settings module reads the environment at import time, so the environment is prepared
here, before any application module is imported. The whole graph (wiring.repositories()) then
runs against a throwaway SQLite file (no Postgres, no broker, a few hundred milliseconds), or
against the Postgres named by TILTHWAVE_TEST_DATABASE_URI when set (CI does both).
"""

import os
import shutil
import tempfile

import pytest

_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="tilthwave-tests-"), "tilthwave.db")
# SQLite by default. CI also runs the suite once on Postgres (TILTHWAVE_TEST_DATABASE_URI), the
# engine production uses: SQLite does not enforce foreign keys, so a test that passes here can
# still hit an IntegrityError there.
_TEST_DB_URI = os.environ.get("TILTHWAVE_TEST_DATABASE_URI") or f"sqlite:///{_TMP_DB}"

os.environ.update(
    {
        "POSTGRES_URI": _TEST_DB_URI,
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

# Everything below sits under the environment block on purpose (E402 is ignored for this file in
# pyproject.toml): the settings module reads os.environ when it is imported.
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import event

from adapters.farm import FarmAdaptor
from adapters.users import UserAdaptor
from adapters.zone import ZoneAdaptor
from common.dates import utc_now
from config.settings import settings
from core.security.password import PasswordHasher
from infrastructure.database.base import Base
from infrastructure.repositories.base import BaseDBRepo
from interfaces.api.helpers.auth import AuthHelper
from interfaces.api.helpers.rate_limit import login_rate_limiter, password_reset_rate_limiter
from interfaces.api.main import app
from interfaces.flow_runner.flow_runner import ZoneAutomaticIrrigationHelper as helper
from wiring import (
    api_use_cases,
    repositories,
)

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

    login_rate_limiter.reset()
    password_reset_rate_limiter.reset()
    yield
    engine = BaseDBRepo.get_engine(settings.DATABASE.URI)
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def repos():

    return repositories()


@pytest.fixture
def use_cases():

    return api_use_cases()


@pytest.fixture
def client():

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def make_farm(repos):

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
def make_user(repos, make_farm):

    def _make(username, role="admin", farm_name=FARM_A, password="Passw0rd-Test!"):
        # users.farm_name is a foreign key: create the farm on demand so a test that only needs a
        # caller does not depend on SQLite ignoring the constraint (Postgres enforces it).
        if farm_name and repos.farm.first([{"attribute": "farm_name", "value": farm_name, "condition": "eq"}]) is None:
            make_farm(farm_name)
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
    The claims are the ones login issues (AuthHelper.session_claims, pfp included), so the suite
    runs on the token shape production uses. Pass user_id to mint a token for a row that does
    not exist.
    """

    def _token(username="admin", role="admin", farm_name=FARM_A, user_id=None):
        if user_id is not None:
            claims = {
                "role": role,
                "username": username,
                "user_id": user_id,
                "user_full_name": username,
                "farm_name": farm_name,
            }
            return AuthHelper.create_access_token(claims)
        user = repos.users.first([{"attribute": "username", "value": username, "condition": "eq"}])
        if user is None:
            user = make_user(username, role=role, farm_name=farm_name)
        elif user.role != role or user.farm_name != farm_name:
            user = repos.users.update(user.id, {"role": role, "farm_name": farm_name})
        return AuthHelper.create_access_token(AuthHelper.session_claims(user))

    return _token


@pytest.fixture(autouse=True)
def _reset_flow_runner_state():
    """
    The control loop keeps its collaborators and failure count as class attributes (set by
    configure()); a test that changes them must not leak into the next one.
    """
    yield

    helper.zone_use_case = helper.irrigation_task_use_case = helper.water_source_use_case = None
    helper.consecutive_failures = 0


@pytest.fixture
def auth_headers(token_for):
    def _headers(**claims):
        return {"Authorization": f"Bearer {token_for(**claims)}"}

    return _headers


@pytest.fixture
def make_zone(repos):

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

    with repo.Session() as session:
        session.get(model, row_id).created_date = utc_now() - timedelta(minutes=minutes)
        session.commit()


@pytest.fixture
def count_statements(repos):
    """Number of SQL statements executed inside the `with` block, on the engine the repos use."""
    engine = repos.sensor_record.engine

    class Counter:
        n = 0

        def __enter__(self):
            self.n = 0
            event.listen(engine, "before_cursor_execute", self._hit)
            return self

        def __exit__(self, *_exc):
            event.remove(engine, "before_cursor_execute", self._hit)

        def _hit(self, *_args):
            self.n += 1

    return Counter()

"""
The shape of the graph after the refactor: no use case builds another, the tenancy rule is one
object that both filters and binds, the unconsumed surface is gone, and lists are lists.
"""

import inspect
import pkgutil

import pytest

import core.use_cases as use_cases_pkg
from common import constants as global_constants
from infrastructure.repositories.tenancy import TenantScope
from tests.conftest import FARM_A


def test_no_use_case_constructs_another_use_case():
    for module_info in pkgutil.iter_modules(use_cases_pkg.__path__):
        module = __import__(f"core.use_cases.{module_info.name}", fromlist=["*"])
        source = inspect.getsource(module)
        body = source[source.index("class ") :] if "class " in source else ""
        assert "UseCase(repo=" not in body, f"{module_info.name} builds a use case inline; inject it from wiring.py"
        assert "circular import" not in source, module_info.name


def test_every_repository_scope_is_a_tenant_scope_or_none(repos):
    for name, repo in vars(repos).items():
        assert repo.TENANT_SCOPE is None or isinstance(repo.TENANT_SCOPE, TenantScope), name


def test_tenant_scope_binds_every_kind_it_filters():
    """A kind that filters reads but does not bind writes is the hole the farm-creation bug was."""
    for kind in (TenantScope.COLUMN, TenantScope.OWN, TenantScope.VIA_ZONE, TenantScope.VIA_SENSOR):
        assert TenantScope(kind, "farm_name").bind({}, None, FARM_A, None) is not None
    with pytest.raises(ValueError):
        TenantScope("elsewhere").bind({}, None, FARM_A, None)


def test_the_unconsumed_surface_is_gone(client, auth_headers, make_farm):
    make_farm(FARM_A)
    headers = auth_headers()
    for path in ("/zones/stats/Zone A", "/sensors/stats/", "/sensors/select-list/", "/farms/identifier/x"):
        assert client.get(path, headers=headers).status_code == 404, path
    assert client.post("/auth/token/verify/", json={"token": "x"}, headers=headers).status_code == 404


def test_irrigation_task_lookups_return_lists(repos, make_farm, make_zone):
    from tests.integration.test_irrigation import RecordingBroker
    from wiring import BrokerRepositories, build_use_cases

    make_farm(FARM_A)
    make_zone("Zone A")
    broker = RecordingBroker()
    zones = build_use_cases(repos, BrokerRepositories(water_source=broker, water_switcher=broker)).zone
    assert zones.get_irrigation_tasks("Zone A", global_constants.IRRIGATION_TASK_IN_PROGRESS) == []
    assert zones.get_all_irrigation_tasks(global_constants.IRRIGATION_TASK_IN_PROGRESS) == []


def test_role_profiles_and_enum_sources():
    roles = global_constants.RESOURCES_FOR_ROLES
    assert roles["admin"] is roles["owner"] and roles["worker"] is roles["engineer"]
    assert global_constants.SENSOR_TYPES == (
        "^(switcher_sensor|source_sensor|temperature_sensor|moisture_sensor|saturation_sensor)$"
    )
    assert global_constants.IRRIGATION_TASK_STATUS == "^(pending|in progress|completed|canceled)$"
    assert global_constants.USER_ROLES == "^(admin|owner|worker|engineer)$"

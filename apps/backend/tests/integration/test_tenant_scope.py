import pytest

from adapters.sensor import SensorAdaptor
from adapters.sensor_record import SensorRecordAdaptor
from common.exceptions import InvalidFilterError, NotFoundError
from common.tenant_context import get_current_tenant, reset_tenant, set_tenant
from infrastructure.scripts.create_admin import bootstrap_admin
from tests.conftest import FARM_A, FARM_B


def test_users_are_scoped_to_the_callers_farm(client, auth_headers, make_farm, make_user):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_user("alice", farm_name=FARM_A)
    make_user("bob", farm_name=FARM_B)
    page = client.get("/users/", headers=auth_headers(farm_name=FARM_A)).json()
    names = {u["username"] for u in page["items"]}
    assert "alice" in names and "bob" not in names  # "admin" is the caller's own row


def test_cross_farm_object_is_404_for_get_patch_and_delete(client, auth_headers, make_farm, make_zone):
    make_farm(FARM_A)
    make_farm(FARM_B)
    zone_b = make_zone("Zone B1", farm_name=FARM_B)
    headers = auth_headers(farm_name=FARM_A)
    assert client.get(f"/zones/{zone_b.id}", headers=headers).status_code == 404
    assert client.patch(f"/zones/{zone_b.id}", json={"size": 1}, headers=headers).status_code == 404
    assert client.delete(f"/zones/{zone_b.id}", headers=headers).status_code == 404


def test_create_cannot_assign_another_farm(client, auth_headers, make_farm, repos):
    make_farm(FARM_A)
    make_farm(FARM_B)
    payload = {
        "farm_name": FARM_B,
        "zone_name": "Zone Sneaky",
        "size": 10,
        "soil_type": "Loamy",
        "moisture_trigger_start": 50,
        "moisture_trigger_stop": 80,
        "saturation_trigger_start": 60,
        "saturation_trigger_stop": 90,
    }
    response = client.post("/zones/", json=payload, headers=auth_headers(farm_name=FARM_A))
    assert response.status_code == 201
    assert response.json()["farm_name"] == FARM_A  # bound to the caller's farm, not the body's
    assert repos.zone.get(response.json()["id"]).farm_name == FARM_A


def test_caller_without_farm_is_refused(client, auth_headers, make_farm, make_zone):
    make_farm(FARM_A)
    make_zone("Zone A")
    assert client.get("/zones/", headers=auth_headers(farm_name=None)).status_code == 401


def test_non_http_callers_run_unscoped(repos, make_farm, make_zone):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_zone("Zone A", farm_name=FARM_A)
    make_zone("Zone B", farm_name=FARM_B)
    assert get_current_tenant() is None
    assert len(repos.zone.filter([])) == 2


def test_farms_list_and_detail_are_scoped_to_the_callers_farm(client, auth_headers, make_farm):
    """The one ("self", ...) scope: the farm row is its own tenant column."""
    make_farm(FARM_A)
    farm_b = make_farm(FARM_B)
    headers = auth_headers(farm_name=FARM_A)
    page = client.get("/farms/", headers=headers).json()
    assert {f["farm_name"] for f in page["items"]} == {FARM_A}
    assert client.get(f"/farms/{farm_b.id}", headers=headers).status_code == 404
    assert client.patch(f"/farms/{farm_b.id}", json={"size": 1}, headers=headers).status_code == 404
    assert client.delete(f"/farms/{farm_b.id}", headers=headers).status_code == 404


def test_farm_scoped_owner_cannot_create_a_farm_under_another_name(client, auth_headers, make_farm, repos):
    """
    Regression: _bind_tenant had no branch for the "self" scope, so an owner could POST any
    farm_name and create a row that nobody could then see or delete through the API.
    """
    make_farm(FARM_A)
    payload = {"farm_name": "Squatted Farm", "address": "1 Nowhere", "size": 5.0}
    response = client.post("/farms/", json=payload, headers=auth_headers(role="owner", farm_name=FARM_A))
    assert response.status_code == 409  # bound to the caller's own farm, which already exists
    assert repos.farm.first([{"attribute": "farm_name", "value": "Squatted Farm", "condition": "eq"}]) is None


def test_bootstrap_creates_the_farm_it_names(repos):
    """The first account is the owner of a farm that may not exist yet: create_admin makes both."""
    owner = bootstrap_admin("first", "Adm1n-Test-Passw0rd!", farm_name="Brand New Farm")
    assert owner.role == "owner" and owner.farm_name == "Brand New Farm"
    assert repos.farm.first([{"attribute": "farm_name", "value": "Brand New Farm", "condition": "eq"}]) is not None
    with pytest.raises(ValueError, match="Farm name"):
        bootstrap_admin("second", "Adm1n-Test-Passw0rd!", farm_name="")


def test_sensor_record_cannot_be_written_into_another_farms_sensor(repos, make_farm):
    """The ("via_sensor",) scope binds writes too, not only reads."""

    make_farm(FARM_A)
    make_farm(FARM_B)
    for serial, farm in (("MSN-A", FARM_A), ("MSN-B", FARM_B)):
        repos.sensor.create(
            SensorAdaptor.dict_to_entity(
                {"serial_number": serial, "type": "moisture_sensor", "is_active": True, "farm_name": farm}
            )
        )

    def record_for(serial):
        return SensorRecordAdaptor.dict_to_entity(
            {"sensor_serial_number": serial, "data": {"type": "moisture", "value": 1}, "performed_by": "tests"}
        )

    token = set_tenant({"username": "alice", "farm_name": FARM_A, "role": "owner", "is_superuser": False})
    try:
        assert repos.sensor_record.create(record_for("MSN-A")).sensor_serial_number == "MSN-A"

        with pytest.raises(NotFoundError):
            repos.sensor_record.create(record_for("MSN-B"))
    finally:
        reset_tenant(token)


def test_private_fields_are_not_filterable(repos, make_farm, make_user):
    """users.password is stripped from every response; it must not be an equality oracle either."""

    make_farm(FARM_A)
    make_user("alice")
    with pytest.raises(InvalidFilterError):
        repos.users.filter([{"attribute": "password", "value": "$2b$anything", "condition": "eq"}])

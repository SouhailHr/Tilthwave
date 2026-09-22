"""
Regression tests for the 2026-09-20 security assessment: sensor tenancy (finding 1), immediate
effect of deactivation / role changes (finding 2), constant-shape login (finding 3) and the
least-privilege simulator account (finding 4).
"""

import pytest

from tests.conftest import FARM_A, FARM_B


@pytest.fixture
def make_sensor(repos):
    from adapters.sensor import SensorAdaptor

    def _make(serial, farm_name=FARM_A, type_="moisture_sensor"):
        return repos.sensor.create(
            SensorAdaptor.dict_to_entity(
                {"serial_number": serial, "type": type_, "is_active": True, "farm_name": farm_name, "performed_by": "t"}
            )
        )

    return _make


@pytest.fixture
def make_record(repos):
    from adapters.sensor_record import SensorRecordAdaptor

    def _make(serial, value=42):
        return repos.sensor_record.create(
            SensorRecordAdaptor.dict_to_entity(
                {"sensor_serial_number": serial, "data": {"type": "moisture", "value": value}, "performed_by": "t"}
            )
        )

    return _make


# ---- finding 1: sensors and sensor records are scoped per farm ------------------------------


def test_sensors_of_another_farm_are_invisible(client, auth_headers, make_farm, make_sensor):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_sensor("A-001", FARM_A)
    foreign = make_sensor("B-001", FARM_B)
    headers = auth_headers(farm_name=FARM_A)

    page = client.get("/sensors/", headers=headers).json()
    assert [s["serial_number"] for s in page["items"]] == ["A-001"]
    assert client.get(f"/sensors/{foreign.id}", headers=headers).status_code == 404
    assert client.patch(f"/sensors/{foreign.id}", json={"is_active": False}, headers=headers).status_code == 404
    assert client.delete(f"/sensors/{foreign.id}", headers=headers).status_code == 404
    assert client.get("/sensors/select-list/", headers=headers).json() == [{"value": "A-001", "label": "A-001"}]


def test_sensor_records_of_another_farm_are_invisible(client, auth_headers, make_farm, make_sensor, make_record):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_sensor("A-001", FARM_A)
    make_sensor("B-001", FARM_B)
    make_record("A-001")
    foreign = make_record("B-001")
    headers = auth_headers(farm_name=FARM_A)

    page = client.get("/sensor-records/", headers=headers).json()
    assert [r["sensor_serial_number"] for r in page["items"]] == ["A-001"]
    filtered = client.get('/sensor-records/?filters={"sensor_serial_number":"B-001"}', headers=headers).json()
    assert filtered["total"] == 0
    assert client.get(f"/sensor-records/{foreign.id}", headers=headers).status_code == 404


def test_created_sensor_belongs_to_the_caller_and_needs_a_visible_zone(
    client, auth_headers, make_farm, make_zone, repos
):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_zone("Zone A", farm_name=FARM_A)
    make_zone("Zone B", farm_name=FARM_B)
    headers = auth_headers(farm_name=FARM_A)
    body = {"type": "moisture_sensor", "serial_number": "NEW-1", "assigned_to_type": "zone", "zone_name": "Zone A"}

    response = client.post("/sensors/", json=body, headers=headers)
    assert response.status_code == 201
    assert response.json()["farm_name"] == FARM_A

    # another farm's zone (or an unknown one) is a 404 and nothing is written
    response = client.post("/sensors/", json={**body, "serial_number": "NEW-2", "zone_name": "Zone B"}, headers=headers)
    assert response.status_code == 404
    assert repos.sensor.first([{"attribute": "serial_number", "value": "NEW-2", "condition": "eq"}]) is None


def test_non_http_callers_see_all_sensors(repos, make_farm, make_sensor):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_sensor("A-001", FARM_A)
    make_sensor("B-001", FARM_B)
    assert len(repos.sensor.filter([])) == 2  # streamer / flow runner run unscoped


# ---- finding 2: a token stops working as soon as the user is deactivated or changed ----------


def test_deactivated_user_is_rejected_before_the_token_expires(client, auth_headers, make_farm, repos):
    make_farm(FARM_A)
    headers = auth_headers(username="mallory")
    assert client.get("/zones/", headers=headers).status_code == 200

    mallory = repos.users.first([{"attribute": "username", "value": "mallory", "condition": "eq"}])
    repos.users.update(mallory.id, {"is_active": False})
    response = client.get("/zones/", headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_token_for_an_unknown_user_is_rejected(client, token_for):
    headers = {"Authorization": f"Bearer {token_for(user_id=999999)}"}
    assert client.get("/zones/", headers=headers).status_code == 401


def test_role_change_takes_effect_on_the_next_request(client, auth_headers, make_farm, repos):
    make_farm(FARM_A)
    headers = auth_headers(username="carol", role="admin")  # token still says admin below
    carol = repos.users.first([{"attribute": "username", "value": "carol", "condition": "eq"}])
    repos.users.update(carol.id, {"role": "worker", "is_superuser": False})

    payload = {"farm_name": FARM_A, "zone_name": "Z", "size": 1, "soil_type": "x"}
    assert client.post("/zones/", json=payload, headers=headers).status_code == 403


def test_farm_comes_from_the_database_not_the_token(client, auth_headers, make_farm, make_zone, repos):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_zone("Zone A", farm_name=FARM_A)
    make_zone("Zone B", farm_name=FARM_B)
    headers = auth_headers(username="dave", farm_name=FARM_A)
    dave = repos.users.first([{"attribute": "username", "value": "dave", "condition": "eq"}])
    repos.users.update(dave.id, {"farm_name": FARM_B})  # moved farms; the old token still claims FARM_A

    page = client.get("/zones/", headers=headers).json()
    assert [z["zone_name"] for z in page["items"]] == ["Zone B"]


# ---- finding 3: login does the same work whether or not the username exists -----------------


def test_unknown_username_still_runs_a_password_check(use_cases, monkeypatch):
    from core.use_cases import users as users_module

    calls = []
    monkeypatch.setattr(
        users_module.PasswordHasher, "verify", staticmethod(lambda pw, hashed: calls.append(hashed) or False)
    )
    assert use_cases.users.authenticate_user("nobody", "whatever") is None
    assert calls == [users_module._UNKNOWN_USER_HASH]


# ---- finding 4: the simulator account is a worker ---------------------------------------------


def test_seed_creates_a_worker_for_the_simulator_when_configured(repos, monkeypatch):
    from infrastructure.scripts import seed_data

    monkeypatch.setenv("SIM_PASSWORD", "Sim-Test-Passw0rd!")
    seed_data.main()
    seed_data.main()
    sim = repos.users.first([{"attribute": "username", "value": "simulator", "condition": "eq"}])
    assert sim.role == "worker" and not sim.is_superuser and sim.is_active and sim.farm_name == "Sunny Farms"
    assert len(repos.users.filter([])) == 2
    assert all(s.farm_name == "Sunny Farms" for s in repos.sensor.filter([]))

"""
HTTP coverage for water sources, water switchers, irrigation tasks and zone-sensor links: create,
list, read, update, delete within the caller's farm, and 404 across farms.
"""

import pytest

from adapters.sensor import SensorAdaptor
from tests.conftest import FARM_A, FARM_B


@pytest.fixture
def two_farms(repos, make_farm, make_zone):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_zone("Zone A", farm_name=FARM_A)
    make_zone("Zone B", farm_name=FARM_B)
    for serial, type_, farm in (
        ("SRC-A", "source_sensor", FARM_A),
        ("SRC-B", "source_sensor", FARM_B),
        ("SWA-A", "switcher_sensor", FARM_A),
        ("MSN-A", "moisture_sensor", FARM_A),
        ("MSN-B", "moisture_sensor", FARM_B),
    ):
        repos.sensor.create(
            SensorAdaptor.dict_to_entity({"serial_number": serial, "type": type_, "is_active": True, "farm_name": farm})
        )


def _source(serial="WS-A", farm=FARM_A, sensor="SRC-A"):
    return {
        "serial_number": serial,
        "farm_name": farm,
        "type": "well",
        "water_pressure": 2.5,
        "water_volume": 5000.0,
        "status": "Off",
        "sensor_serial_number": sensor,
    }


def _crud(client, headers, resource, create_body, patch_body, patched_field):
    created = client.post(f"/{resource}/", json=create_body, headers=headers)
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    listed = client.get(f"/{resource}/", headers=headers).json()
    assert [row["id"] for row in listed["items"]] == [item_id]
    assert client.get(f"/{resource}/{item_id}", headers=headers).json() == listed["items"][0]
    patched = client.patch(f"/{resource}/{item_id}", json=patch_body, headers=headers)
    assert patched.status_code == 200 and patched.json()[patched_field] == patch_body[patched_field]
    assert client.delete(f"/{resource}/{item_id}", headers=headers).status_code == 204
    assert client.get(f"/{resource}/{item_id}", headers=headers).status_code == 404
    return item_id


def test_water_sources_crud_and_farm_isolation(client, auth_headers, two_farms, repos):
    headers = auth_headers(farm_name=FARM_A)
    _crud(client, headers, "water-sources", _source(), {"status": "On"}, "status")
    # the farm column is bound to the caller's farm whatever the body says
    created = client.post("/water-sources/", json=_source(farm=FARM_B), headers=headers).json()
    assert created["farm_name"] == FARM_A
    # the other farm's source is invisible in every verb
    foreign = client.post(
        "/water-sources/", json=_source("WS-B", FARM_B, "SRC-B"), headers=auth_headers(username="b", farm_name=FARM_B)
    ).json()
    for verb, kwargs in (("get", {}), ("patch", {"json": {"status": "On"}}), ("delete", {})):
        assert getattr(client, verb)(f"/water-sources/{foreign['id']}", headers=headers, **kwargs).status_code == 404
    # only a source sensor may be attached
    bad = client.post("/water-sources/", json=_source("WS-X", sensor="MSN-A"), headers=headers)
    assert bad.status_code == 422 and "source_sensor" in bad.json()["detail"]


def test_water_switchers_crud_and_farm_isolation(client, auth_headers, two_farms):
    headers = auth_headers(farm_name=FARM_A)
    client.post("/water-sources/", json=_source(), headers=headers)
    switcher = {
        "serial_number": "SW-A",
        "status": "Off",
        "water_source_serial_number": "WS-A",
        "zone_name": "Zone A",
        "sensor_serial_number": "SWA-A",
    }
    _crud(client, headers, "water-switchers", switcher, {"status": "On"}, "status")
    # a switcher cannot be placed in another farm's zone
    foreign_zone = client.post("/water-switchers/", json={**switcher, "zone_name": "Zone B"}, headers=headers)
    assert foreign_zone.status_code == 404


def test_irrigation_tasks_crud_and_farm_isolation(client, auth_headers, two_farms):
    headers = auth_headers(farm_name=FARM_A)
    task = {"zone_name": "Zone A", "status": "pending"}
    _crud(client, headers, "irrigation-tasks", task, {"status": "canceled"}, "status")
    other = auth_headers(username="b", farm_name=FARM_B)
    foreign = client.post("/irrigation-tasks/", json={"zone_name": "Zone B", "status": "pending"}, headers=other).json()
    assert client.get("/irrigation-tasks/", headers=headers).json()["total"] == 0
    assert client.get(f"/irrigation-tasks/{foreign['id']}", headers=headers).status_code == 404
    assert (
        client.patch(f"/irrigation-tasks/{foreign['id']}", json={"status": "canceled"}, headers=headers).status_code
        == 404
    )


def test_zone_sensor_links_crud_and_attach_rule(client, auth_headers, two_farms):
    headers = auth_headers(farm_name=FARM_A)
    link = {"zone_name": "Zone A", "sensor_serial_number": "MSN-A"}
    _crud(client, headers, "zone-sensors", link, {"zone_name": "Zone A"}, "zone_name")
    # only zone sensor types may be linked, and only the caller's sensors
    assert (
        client.post("/zone-sensors/", json={**link, "sensor_serial_number": "SRC-A"}, headers=headers).status_code
        == 422
    )
    assert (
        client.post("/zone-sensors/", json={**link, "sensor_serial_number": "MSN-B"}, headers=headers).status_code
        == 422
    )

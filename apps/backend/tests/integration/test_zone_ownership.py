"""
Rows linked to a zone (trees, switchers, irrigation tasks, zone-sensor links) can only be
written into the caller's own zones. Another farm's zone is "not found", never "forbidden".
"""

from datetime import date

from adapters.sensor import SensorAdaptor
from adapters.tree import TreeAdaptor
from tests.conftest import FARM_A, FARM_B


def _two_farms(make_farm, make_zone):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_zone("Zone A", farm_name=FARM_A)
    make_zone("Zone B", farm_name=FARM_B)


def test_irrigation_task_cannot_target_another_farms_zone(client, auth_headers, make_farm, make_zone, repos):
    _two_farms(make_farm, make_zone)
    response = client.post(
        "/irrigation-tasks/",
        json={"zone_name": "Zone B", "status": "in progress"},
        headers=auth_headers(farm_name=FARM_A),
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Zone not found"}
    assert repos.irrigation_task.filter([]) == []


def test_tree_create_and_move_stay_within_the_callers_farm(client, auth_headers, make_farm, make_zone):
    _two_farms(make_farm, make_zone)
    headers = auth_headers(farm_name=FARM_A)
    tree = {
        "serial_number": "T1",
        "zone_name": "Zone A",
        "variety": "olive",
        "planting_date": "2020-01-01",
        "height": 1.0,
        "width_diameter": 1.0,
        "trunk_diameter": 1.0,
    }
    created = client.post("/trees/", json=tree, headers=headers)
    assert created.status_code == 201
    foreign = client.post("/trees/", json={**tree, "serial_number": "T2", "zone_name": "Zone B"}, headers=headers)
    assert foreign.status_code == 404
    moved = client.patch(f"/trees/{created.json()['id']}", json={"zone_name": "Zone B"}, headers=headers)
    assert moved.status_code == 404


def test_zone_sensor_link_cannot_attach_to_another_farms_zone(client, auth_headers, make_farm, make_zone, repos):
    _two_farms(make_farm, make_zone)
    repos.sensor.create(
        SensorAdaptor.dict_to_entity(
            {"serial_number": "MSN9", "type": "moisture_sensor", "is_active": True, "farm_name": FARM_A}
        )
    )
    response = client.post(
        "/zone-sensors/",
        json={"zone_name": "Zone B", "sensor_serial_number": "MSN9"},
        headers=auth_headers(farm_name=FARM_A),
    )
    assert response.status_code == 404


def test_workers_and_scripts_are_not_bound(repos, make_farm, make_zone):
    _two_farms(make_farm, make_zone)
    tree = repos.tree.create(
        TreeAdaptor.dict_to_entity(
            {
                "serial_number": "T1",
                "zone_name": "Zone B",
                "variety": "olive",
                "planting_date": date(2020, 1, 1),
                "height": 1.0,
                "width_diameter": 1.0,
                "trunk_diameter": 1.0,
            }
        )
    )
    assert tree.zone_name == "Zone B"  # no tenant context: seed / flow runner can write anywhere

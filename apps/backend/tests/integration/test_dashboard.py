"""
GET /dashboard/summary/: one round trip for the home page, counted in the database and scoped to
the caller's farm. Rows are created through the repositories (non-HTTP, so unscoped) for two
farms, then read back as a FARM_A caller.
"""

from adapters.irrigation_task import IrrigationTaskAdaptor
from adapters.sensor import SensorAdaptor
from adapters.water_source import WaterSourceAdaptor
from adapters.water_switcher import WaterSwitcherAdaptor
from tests.conftest import FARM_A, FARM_B

PERFORMED_BY = "tests"


def _sensor(repos, serial, farm_name, is_active=True):
    return repos.sensor.create(
        SensorAdaptor.dict_to_entity(
            {
                "serial_number": serial,
                "type": "moisture_sensor",
                "is_active": is_active,
                "farm_name": farm_name,
                "performed_by": PERFORMED_BY,
            }
        )
    )


def _water_source(repos, serial, farm_name, status):
    return repos.water_source.create(
        WaterSourceAdaptor.dict_to_entity(
            {
                "serial_number": serial,
                "farm_name": farm_name,
                "type": "well",
                "water_pressure": 1.0,
                "water_volume": 1.0,
                "status": status,
                "sensor_serial_number": None,
                "performed_by": PERFORMED_BY,
            }
        )
    )


def _water_switcher(repos, serial, zone_name, status):
    return repos.water_switcher.create(
        WaterSwitcherAdaptor.dict_to_entity(
            {
                "serial_number": serial,
                "status": status,
                "water_source_serial_number": None,
                "zone_name": zone_name,
                "sensor_serial_number": None,
                "performed_by": PERFORMED_BY,
            }
        )
    )


def _task(repos, zone_name, status):
    return repos.irrigation_task.create(
        IrrigationTaskAdaptor.dict_to_entity({"zone_name": zone_name, "status": status, "performed_by": PERFORMED_BY})
    )


def _two_farms(repos, make_farm, make_zone):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_zone("Zone A", farm_name=FARM_A)
    make_zone("Zone B", farm_name=FARM_B)

    _sensor(repos, "A-S1", FARM_A)
    _sensor(repos, "A-S2", FARM_A)
    _sensor(repos, "A-S3", FARM_A, is_active=False)
    _sensor(repos, "B-S1", FARM_B)

    _water_source(repos, "A-WS1", FARM_A, "On")
    _water_source(repos, "A-WS2", FARM_A, "Error")
    _water_source(repos, "B-WS1", FARM_B, "On")

    _water_switcher(repos, "A-SW1", "Zone A", "On")
    _water_switcher(repos, "A-SW2", "Zone A", "Off")
    _water_switcher(repos, "A-SW3", "Zone A", "Error")
    _water_switcher(repos, "B-SW1", "Zone B", "Error")

    # 8 tasks for Zone A so recent_tasks (capped at 6, newest first) has something to drop.
    for status in ["pending", "in progress", "in progress", "completed", "canceled"] + ["completed"] * 3:
        _task(repos, "Zone A", status)
    _task(repos, "Zone B", "pending")


def test_summary_counts_in_the_database_and_scopes_to_the_callers_farm(
    client, auth_headers, make_farm, make_zone, repos
):
    _two_farms(repos, make_farm, make_zone)

    response = client.get("/dashboard/summary/", headers=auth_headers(farm_name=FARM_A))
    assert response.status_code == 200
    body = response.json()

    assert body["sensors"] == {"total": 3, "active": 2, "inactive": 1, "unknown": 0}
    assert body["water_sources"] == {"total": 2, "On": 1, "Off": 0, "Error": 1}
    assert body["water_switchers"] == {"total": 3, "On": 1, "Off": 1, "Error": 1}
    assert body["irrigation_tasks"] == {
        "total": 8,
        "pending": 1,
        "in progress": 2,
        "completed": 4,
        "canceled": 1,
    }
    assert body["farms"] == {"total": 1}
    assert body["zones"] == {"total": 1}

    recent = body["recent_tasks"]
    assert len(recent) == 6
    assert [t["id"] for t in recent] == sorted((t["id"] for t in recent), reverse=True)
    assert {t["zone_name"] for t in recent} == {"Zone A"}  # never the other farm's tasks

    farm = body["farm"]
    assert farm["farm_name"] == FARM_A
    assert farm["total_zones"] == 1
    assert farm["total_water_sources"] == 2
    assert set(farm) >= {"total_zones", "total_water_sources", "total_water_switchers", "total_trees", "chart_data"}


def test_summary_is_readable_by_every_role(client, auth_headers, make_farm):
    make_farm(FARM_A)
    for role in ("admin", "owner", "worker", "engineer"):
        response = client.get("/dashboard/summary/", headers=auth_headers(username=f"u-{role}", role=role))
        assert response.status_code == 200, role


def test_summary_requires_a_token(client):
    assert client.get("/dashboard/summary/").status_code == 401


def test_caller_without_a_farm_is_not_authenticated(client, auth_headers, make_farm, make_zone, repos):
    _two_farms(repos, make_farm, make_zone)
    response = client.get("/dashboard/summary/", headers=auth_headers(username="nofarm", farm_name=None))
    assert response.status_code == 401

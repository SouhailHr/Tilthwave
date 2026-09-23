"""
Fixes from the 2026-09-23 re-run: sensors are created atomically and read the same on write as
on read, moving a sensor leaves no stale link, an unhandled error still carries its request id,
a database outage is a 503, the dashboard has a statement budget, the latest-reading scan is
time-bounded, and past months of consumption are not re-summed on every poll.
"""

from datetime import datetime, timedelta

from adapters.sensor import SensorAdaptor
from adapters.sensor_record import SensorRecordAdaptor
from adapters.water_source import WaterSourceAdaptor
from adapters.water_switcher import WaterSwitcherAdaptor
from common.dates import utc_now
from infrastructure.exceptions import DBReposException
from infrastructure.repositories.base import BaseDBRepo
from interfaces.api.main import app
from tests.conftest import FARM_A


def _sensor(repos, serial, type_, farm=FARM_A):
    return repos.sensor.create(
        SensorAdaptor.dict_to_entity({"serial_number": serial, "type": type_, "is_active": True, "farm_name": farm})
    )


def test_sensor_create_is_atomic_and_answers_with_the_read_shape(client, auth_headers, make_farm, make_zone, repos):
    make_farm(FARM_A)
    make_zone("Zone A")
    headers = auth_headers()
    mismatch = {
        "serial_number": "SW-1",
        "type": "switcher_sensor",
        "is_active": True,
        "assigned_to_type": "zone",
        "zone_name": "Zone A",
    }
    response = client.post("/sensors/", json=mismatch, headers=headers)
    assert response.status_code == 422 and "switcher_sensor" not in response.json()["detail"]
    assert (
        repos.sensor.first([{"attribute": "serial_number", "value": "SW-1", "condition": "eq"}]) is None
    )  # nothing left behind
    ok = client.post("/sensors/", json={**mismatch, "type": "moisture_sensor"}, headers=headers)
    assert ok.status_code == 201 and ok.json()["assigned_to"] == "Zone A"  # the corrected retry is not a 409
    patched = client.patch(f"/sensors/{ok.json()['id']}", json={"is_active": False}, headers=headers)
    assert patched.json()["assigned_to"] == "Zone A"


def test_moving_a_sensor_leaves_no_stale_link(client, auth_headers, make_farm, make_zone, repos):
    make_farm(FARM_A)
    make_zone("Zone A")
    make_zone("Zone B")
    for serial, type_ in (("SRC-1", "source_sensor"), ("SWA-1", "switcher_sensor"), ("SWA-2", "switcher_sensor")):
        _sensor(repos, serial, type_)
    repos.water_source.create(
        WaterSourceAdaptor.dict_to_entity(
            {
                "serial_number": "WS-1",
                "farm_name": FARM_A,
                "type": "well",
                "water_pressure": 1.0,
                "water_volume": 1.0,
                "status": "Off",
                "sensor_serial_number": "SRC-1",
            }
        )
    )
    for serial, sensor in (("SW-1", "SWA-1"), ("SW-2", "SWA-2")):
        repos.water_switcher.create(
            WaterSwitcherAdaptor.dict_to_entity(
                {
                    "serial_number": serial,
                    "status": "Off",
                    "water_source_serial_number": "WS-1",
                    "zone_name": "Zone A",
                    "sensor_serial_number": sensor,
                }
            )
        )
    headers = auth_headers()
    moisture = client.post(
        "/sensors/",
        json={
            "serial_number": "M-1",
            "type": "moisture_sensor",
            "is_active": True,
            "assigned_to_type": "zone",
            "zone_name": "Zone A",
        },
        headers=headers,
    ).json()
    # zone A -> zone B: one link row, pointing at B
    assert (
        client.patch(
            f"/sensors/{moisture['id']}", json={"assigned_to_type": "zone", "zone_name": "Zone B"}, headers=headers
        ).json()["assigned_to"]
        == "Zone B"
    )
    links = repos.zone_sensors.filter([{"attribute": "sensor_serial_number", "value": "M-1", "condition": "eq"}])
    assert [link.zone_name for link in links] == ["Zone B"]
    # switcher sensor SWA-1 from SW-1 to SW-2: SW-1 no longer claims it
    swa1 = repos.sensor.first([{"attribute": "serial_number", "value": "SWA-1", "condition": "eq"}])
    moved = client.patch(
        f"/sensors/{swa1.id}", json={"assigned_to_type": "water_switcher", "water_switcher": "SW-2"}, headers=headers
    )
    assert moved.status_code == 200 and moved.json()["assigned_to"] == "SW-2"
    by_serial = {s.serial_number: s.sensor_serial_number for s in repos.water_switcher.filter([])}
    assert by_serial == {"SW-1": None, "SW-2": "SWA-1"}


def test_an_unhandled_error_still_carries_its_request_id(client):
    def boom():
        raise RuntimeError("boom")

    app.add_api_route(
        "/health/__boom", boom, methods=["GET"]
    )  # under /health: public, so the failure is the endpoint's
    try:
        response = client.get("/health/__boom", headers={"X-Request-ID": "trace-boom-1"})
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/health/__boom"]
    assert response.status_code == 500
    assert response.headers["x-request-id"] == "trace-boom-1"
    body = response.json()
    assert body["error_code"] == "internal_error" and body["request_id"] == "trace-boom-1"


def test_a_database_outage_is_a_503_with_retry_after(client, auth_headers, make_farm, monkeypatch):
    make_farm(FARM_A)
    headers = auth_headers()

    def down(self, *_args, **_kwargs):
        raise DBReposException("connection refused")

    monkeypatch.setattr(BaseDBRepo, "paginate", down)
    response = client.get("/zones/", headers=headers)
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert response.json()["error_code"] == "database_unavailable"


def test_dashboard_summary_stays_within_its_statement_budget(repos, use_cases, make_farm, make_zone, count_statements):
    make_farm(FARM_A)
    make_zone("Zone A")
    for i in range(3):
        _sensor(repos, f"S{i}", "moisture_sensor")
    from common.tenant_context import reset_tenant, set_tenant  # noqa: PLC0415

    token = set_tenant({"username": "a", "farm_name": FARM_A, "role": "admin", "is_superuser": True})
    try:
        with count_statements as counted:
            summary = use_cases.dashboard.summary()
    finally:
        reset_tenant(token)
    assert summary["sensors"] == {"total": 3, "active": 3, "inactive": 0, "unknown": 0}
    assert summary["water_sources"]["total"] == 0 and summary["irrigation_tasks"]["total"] == 0
    # recent tasks 1, sensors 1, three GROUP BYs, farms 1, zones 1, primary farm 1 + its 5 stats
    assert counted.n <= 13


def test_latest_per_sensor_ignores_records_older_than_since(repos, make_farm):
    make_farm(FARM_A)
    _sensor(repos, "M-1", "moisture_sensor")
    old = repos.sensor_record.create(
        SensorRecordAdaptor.dict_to_entity({"sensor_serial_number": "M-1", "data": {"value": 1}, "performed_by": "t"})
    )
    from infrastructure.database.tables.sensor_record import SensorRecord  # noqa: PLC0415

    with repos.sensor_record.Session() as session:
        session.get(SensorRecord, old.id).created_date = utc_now() - timedelta(minutes=90)
        session.commit()
    assert repos.sensor_record.latest_per_sensor(["M-1"]) != []
    assert repos.sensor_record.latest_per_sensor(["M-1"], since=utc_now() - timedelta(minutes=30)) == []


def test_past_months_of_consumption_are_summed_once(repos, use_cases, make_farm, monkeypatch):
    make_farm(FARM_A)
    _sensor(repos, "SRC-1", "source_sensor")
    repos.water_source.create(
        WaterSourceAdaptor.dict_to_entity(
            {
                "serial_number": "WS-1",
                "farm_name": FARM_A,
                "type": "well",
                "water_pressure": 1.0,
                "water_volume": 1.0,
                "status": "Off",
                "sensor_serial_number": "SRC-1",
            }
        )
    )
    calls = []
    real = repos.sensor_record.monthly_consumption

    def spy(serials, year, from_month=1):
        calls.append(from_month)
        return real(serials, year, from_month)

    monkeypatch.setattr(repos.sensor_record, "monthly_consumption", spy)
    use_cases.farm.get_stats(name=FARM_A)
    use_cases.farm.get_stats(name=FARM_A)
    assert calls == [1, datetime.now().month]  # whole year once, then only the current month

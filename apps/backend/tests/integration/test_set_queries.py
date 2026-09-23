"""
The questions asked per tick and per dashboard poll are answered in a fixed number of queries,
whatever the number of zones, sensors or records.
"""

from datetime import datetime

import interfaces.flow_runner.flow_runner as flow_runner
from adapters.sensor import SensorAdaptor
from adapters.sensor_record import SensorRecordAdaptor
from adapters.zone_sensors import ZoneSensorsAdaptor
from common.tenant_context import reset_tenant, set_tenant
from infrastructure.database.tables.sensor_record import SensorRecord
from tests.conftest import FARM_A, FARM_B
from tests.integration.test_irrigation import RecordingBroker, _use_cases_with


def _sensor(repos, serial, type_="moisture_sensor", farm=None):
    data = {"serial_number": serial, "type": type_, "is_active": True}
    if farm:
        data["farm_name"] = farm
    return repos.sensor.create(SensorAdaptor.dict_to_entity(data))


def _record(repos, serial, data):
    return repos.sensor_record.create(
        SensorRecordAdaptor.dict_to_entity({"sensor_serial_number": serial, "data": data, "performed_by": "tests"})
    )


def test_latest_per_sensor_returns_the_newest_row_of_each_sensor_in_one_query(repos, make_farm, count_statements):
    make_farm(FARM_A)
    for serial in ("A", "B", "C"):
        _sensor(repos, serial)
        for value in (1, 2, 3):
            _record(repos, serial, {"type": "moisture", "value": value})
    with count_statements as counted:
        latest = repos.sensor_record.latest_per_sensor(["A", "B"])
    assert counted.n == 1
    assert {r.sensor_serial_number: r.data["value"] for r in latest} == {"A": 3, "B": 3}


def test_latest_per_sensor_is_tenant_scoped(repos, make_farm):
    make_farm(FARM_A)
    make_farm(FARM_B)
    _sensor(repos, "A1", farm=FARM_A)
    _sensor(repos, "B1", farm=FARM_B)
    _record(repos, "A1", {"type": "moisture", "value": 1})
    _record(repos, "B1", {"type": "moisture", "value": 1})
    token = set_tenant({"username": "alice", "farm_name": FARM_A, "role": "owner", "is_superuser": False})
    try:
        assert [r.sensor_serial_number for r in repos.sensor_record.latest_per_sensor(["A1", "B1"])] == ["A1"]
    finally:
        reset_tenant(token)


def test_count_by_groups_in_one_query(repos, make_farm, count_statements):
    make_farm(FARM_A)
    _sensor(repos, "S1")
    _sensor(repos, "S2")
    repos.sensor.create(
        SensorAdaptor.dict_to_entity({"serial_number": "S3", "type": "moisture_sensor", "is_active": False})
    )
    with count_statements as counted:
        counts = repos.sensor.count_by("is_active")
    assert counted.n == 1
    assert counts == {True: 2, False: 1}


def test_monthly_consumption_sums_in_the_database(repos, make_farm, count_statements):
    make_farm(FARM_A)
    _sensor(repos, "SRC", "source_sensor")
    year = datetime.now().year
    for month, amount in ((1, 10.5), (1, 4.5), (3, 7)):
        record = _record(repos, "SRC", {"type": "source", "consumption": amount})
        with repos.sensor_record.Session() as session:
            session.get(SensorRecord, record.id).created_date = datetime(year, month, 15)
            session.commit()
    _record(repos, "SRC", {"type": "source"})  # no consumption key: ignored, not an error
    with count_statements as counted:
        monthly = repos.sensor_record.monthly_consumption(["SRC"], year)
    assert counted.n == 1
    assert monthly[1] == 15.0 and monthly[3] == 7.0 and 2 not in monthly


def test_a_tick_costs_the_same_number_of_queries_for_one_zone_and_for_five(
    repos, make_farm, make_zone, count_statements
):
    """Regression for the O(zones x sensors) tick: zones with sensors but nothing to start."""

    helper = flow_runner.ZoneAutomaticIrrigationHelper
    make_farm(FARM_A)

    def zone_with_sensor(name):
        make_zone(name)
        _sensor(repos, f"M-{name}")
        repos.zone_sensors.create(
            ZoneSensorsAdaptor.dict_to_entity({"zone_name": name, "sensor_serial_number": f"M-{name}"})
        )
        _record(repos, f"M-{name}", {"type": "moisture", "value": 90})

    zone_with_sensor("Zone 1")
    helper.configure(_use_cases_with(repos, RecordingBroker()))
    with count_statements as one_zone:
        helper.auto_irrigation()
    for i in range(2, 6):
        zone_with_sensor(f"Zone {i}")
    with count_statements as five_zones:
        helper.auto_irrigation()
    assert five_zones.n == one_zone.n
    assert one_zone.n <= 6


def test_sensor_list_enriches_a_page_in_a_fixed_number_of_queries(
    client, auth_headers, make_farm, make_zone, repos, count_statements
):
    make_farm(FARM_A)
    make_zone("Zone A")
    for i in range(12):
        _sensor(repos, f"M{i}", farm=FARM_A)
        repos.zone_sensors.create(
            ZoneSensorsAdaptor.dict_to_entity({"zone_name": "Zone A", "sensor_serial_number": f"M{i}"})
        )
    headers = auth_headers()
    with count_statements as counted:
        page = client.get("/sensors/?size=12", headers=headers).json()
    assert {item["assigned_to"] for item in page["items"]} == {"Zone A"}
    # tenant user lookup + count + page + three link tables at most: nothing per row
    assert counted.n <= 7

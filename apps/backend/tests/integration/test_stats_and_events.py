from adapters.sensor import SensorAdaptor
from adapters.water_source import WaterSourceAdaptor
from adapters.water_switcher import WaterSwitcherAdaptor
from core.use_cases.exceptions import UseCaseException
from tests.conftest import FARM_A


def test_tree_stats_on_an_empty_table_is_200(client, auth_headers):
    response = client.get("/trees/stats/", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["total_trees"] == 0
    assert isinstance(response.json()["tree_average_age"], str)


def test_health_reports_503_when_the_database_is_unreachable(client, monkeypatch):
    from infrastructure.repositories.base import BaseDBRepo

    def broken(*_args, **_kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(BaseDBRepo, "get_engine", staticmethod(broken))
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unreachable"}


def test_status_event_updates_the_switcher_then_records_it(repos, make_farm, make_zone):
    from interfaces.streamer.event_handler import EventHandler

    make_farm(FARM_A)
    make_zone("Zone A")
    repos.sensor.create(
        SensorAdaptor.dict_to_entity({"serial_number": "SWA1", "type": "switcher_sensor", "is_active": True})
    )
    repos.water_switcher.create(
        WaterSwitcherAdaptor.dict_to_entity(
            {
                "serial_number": "SW1",
                "status": "Off",
                "water_source_serial_number": None,
                "zone_name": "Zone A",
                "sensor_serial_number": "SWA1",
            }
        )
    )
    EventHandler().process(
        {
            "event_type": "status_data",
            "sensor_serial_number": "SWA1",
            "data": {"type": "switcher", "status": "On", "timestamp": "x"},
        }
    )
    assert repos.water_switcher.first([]).status == "On"
    assert len(repos.sensor_record.filter([])) == 1


def test_unknown_events_are_rejected_not_swallowed():
    import pytest

    from interfaces.streamer.event_handler import EventHandler

    for event in ({}, {"event_type": "bogus"}, {"event_type": "status_data", "data": {"type": "valve"}}):
        with pytest.raises(UseCaseException):
            EventHandler().process(dict(event))


def test_status_event_updates_the_source_then_records_it(repos, make_farm):
    from interfaces.streamer.event_handler import EventHandler

    make_farm(FARM_A)
    repos.sensor.create(
        SensorAdaptor.dict_to_entity({"serial_number": "SRC1", "type": "source_sensor", "is_active": True})
    )
    repos.water_source.create(
        WaterSourceAdaptor.dict_to_entity(
            {
                "serial_number": "WS1",
                "farm_name": FARM_A,
                "type": "well",
                "water_pressure": 2.5,
                "water_volume": 5000.0,
                "status": "Off",
                "sensor_serial_number": "SRC1",
            }
        )
    )
    EventHandler().process(
        {
            "event_type": "status_data",
            "sensor_serial_number": "SRC1",
            "data": {"type": "source", "status": "On", "timestamp": "x"},
        }
    )
    assert repos.water_source.first([]).status == "On"
    assert len(repos.sensor_record.filter([])) == 1


def test_data_record_event_saves_the_reading_and_touches_no_actuator(repos, make_farm, make_zone):
    from interfaces.streamer.event_handler import EventHandler

    make_farm(FARM_A)
    make_zone("Zone A")
    repos.sensor.create(
        SensorAdaptor.dict_to_entity({"serial_number": "MSN1", "type": "moisture_sensor", "is_active": True})
    )
    repos.sensor.create(
        SensorAdaptor.dict_to_entity({"serial_number": "SWA1", "type": "switcher_sensor", "is_active": True})
    )
    repos.water_switcher.create(
        WaterSwitcherAdaptor.dict_to_entity(
            {
                "serial_number": "SW1",
                "status": "Off",
                "water_source_serial_number": None,
                "zone_name": "Zone A",
                "sensor_serial_number": "SWA1",
            }
        )
    )
    EventHandler().process(
        {
            "event_type": "data_record",
            "sensor_serial_number": "MSN1",
            "data": {"type": "moisture", "value": 42, "timestamp": "2026-09-22 10:00:00"},
        }
    )
    records = repos.sensor_record.filter([])
    assert len(records) == 1
    assert records[0].sensor_serial_number == "MSN1"
    assert records[0].performed_by == "streamer"
    assert records[0].data["value"] == 42
    assert repos.water_switcher.first([]).status == "Off"

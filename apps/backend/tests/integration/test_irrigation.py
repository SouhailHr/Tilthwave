"""
Irrigation safety: commands go out before state is recorded, a failed command changes nothing,
and the flow runner's hard limits win over the zone triggers.
"""

from datetime import timedelta

import pytest

import common.constants as global_constants
from adapters.sensor import SensorAdaptor
from adapters.sensor_record import SensorRecordAdaptor
from adapters.water_source import WaterSourceAdaptor
from adapters.water_switcher import WaterSwitcherAdaptor
from adapters.zone_sensors import ZoneSensorsAdaptor
from common.dates import utc_now
from common.exceptions import BrokerError
from infrastructure.repositories.base import BaseBrokerRepo
from tests.conftest import FARM_A
from wiring import BrokerRepositories, build_use_cases


class RecordingBroker(BaseBrokerRepo):
    def __init__(self, fail=False):
        super().__init__(producer=None, random_broker="test")
        self.fail, self.commands = fail, []

    def push_event_to_broker(self, topic, key, event):
        if self.fail:
            raise BrokerError("broker down")
        self.commands.append(event)


@pytest.fixture
def farm_with_zone(repos, make_farm, make_zone):
    make_farm(FARM_A)
    zone = make_zone("Zone A")
    for serial, type_ in [
        ("SRC001", "source_sensor"),
        ("SWA001", "switcher_sensor"),
        ("MSN1", "moisture_sensor"),
        ("SAT1", "saturation_sensor"),
    ]:
        repos.sensor.create(SensorAdaptor.dict_to_entity({"serial_number": serial, "type": type_, "is_active": True}))
    repos.water_source.create(
        WaterSourceAdaptor.dict_to_entity(
            {
                "serial_number": "WS001",
                "farm_name": FARM_A,
                "type": "well",
                "water_pressure": 2.5,
                "water_volume": 5000.0,
                "status": "Off",
                "sensor_serial_number": "SRC001",
            }
        )
    )
    repos.water_switcher.create(
        WaterSwitcherAdaptor.dict_to_entity(
            {
                "serial_number": "SWITA01",
                "status": "Off",
                "water_source_serial_number": "WS001",
                "zone_name": "Zone A",
                "sensor_serial_number": "SWA001",
            }
        )
    )
    for serial in ("MSN1", "SAT1"):
        repos.zone_sensors.create(
            ZoneSensorsAdaptor.dict_to_entity({"zone_name": "Zone A", "sensor_serial_number": serial})
        )
    return zone


def _use_cases_with(repos, broker):
    return build_use_cases(repos, BrokerRepositories(water_source=broker, water_switcher=broker))


def test_start_irrigation_publishes_source_then_switcher_then_records_the_task(repos, farm_with_zone):
    broker = RecordingBroker()
    zone_uc = _use_cases_with(repos, broker).zone
    task = zone_uc.start_irrigation("Zone A")
    assert task.status == global_constants.IRRIGATION_TASK_IN_PROGRESS
    assert [(c["data"]["type"], c["data"]["status"]) for c in broker.commands] == [("source", "On"), ("switcher", "On")]
    assert all(c["data"]["timestamp"] for c in broker.commands)  # computed per command, not at import


def test_failed_command_creates_no_task(repos, farm_with_zone):
    zone_uc = _use_cases_with(repos, RecordingBroker(fail=True)).zone
    with pytest.raises(BrokerError):
        zone_uc.start_irrigation("Zone A")
    assert repos.irrigation_task.filter([]) == []


def test_stop_irrigation_publishes_off_then_completes_with_utc_duration(repos, farm_with_zone):
    broker = RecordingBroker()
    zone_uc = _use_cases_with(repos, broker).zone
    task = zone_uc.start_irrigation("Zone A")
    with repos.irrigation_task.Session() as session:  # backdate 5 minutes, in UTC like the DB default
        from infrastructure.database.tables.irrigation_task import IrrigationTask

        row = session.get(IrrigationTask, task.id)
        row.created_date = utc_now() - timedelta(minutes=5)
        session.commit()
    broker.commands.clear()
    done = zone_uc.stop_irrigation(repos.irrigation_task.get(task.id))
    assert done.status == global_constants.IRRIGATION_TASK_COMPLETED
    assert 4 <= done.duration <= 6  # not 125: the local TZ never leaks in
    assert broker.commands[0]["data"] == {
        "type": "switcher",
        "status": "Off",
        "timestamp": broker.commands[0]["data"]["timestamp"],
    }


def _record(repos, serial, type_, value, age_minutes=0):
    entity = repos.sensor_record.create(
        SensorRecordAdaptor.dict_to_entity(
            {"sensor_serial_number": serial, "data": {"type": type_, "value": value, "timestamp": "x"}}
        )
    )
    if age_minutes:
        from infrastructure.database.tables.sensor_record import SensorRecord

        with repos.sensor_record.Session() as session:
            session.get(SensorRecord, entity.id).created_date = utc_now() - timedelta(minutes=age_minutes)
            session.commit()


def _clear_records(repos):
    for record in repos.sensor_record.filter([]):
        repos.sensor_record.delete(record.id)


def test_flow_runner_hard_limits(repos, farm_with_zone):
    from interfaces.flow_runner.flow_runner import ZoneAutomaticIrrigationHelper as helper

    use_cases = _use_cases_with(repos, RecordingBroker())
    helper.configure(use_cases)
    zone = repos.zone.first([]).to_dict()

    # fresh, low readings -> start
    _record(repos, "MSN1", "moisture", 20)
    _record(repos, "SAT1", "saturation", 30)
    assert helper._check_start_stop(zone, None) == (helper.START, "start trigger reached")

    # only stale readings -> never start, and stop a running task
    _clear_records(repos)
    _record(repos, "MSN1", "moisture", 20, age_minutes=45)
    _record(repos, "SAT1", "saturation", 30, age_minutes=45)
    assert helper._check_start_stop(zone, None) == (None, None)
    task = use_cases.zone.start_irrigation("Zone A")
    assert helper._check_start_stop(zone, task) == (helper.STOP, "no fresh readings")

    # running longer than MAX_IRRIGATION_MINUTES -> hard stop even with fresh, dry readings
    _record(repos, "MSN1", "moisture", 20)
    _record(repos, "SAT1", "saturation", 30)
    from infrastructure.database.tables.irrigation_task import IrrigationTask

    with repos.irrigation_task.Session() as session:
        session.get(IrrigationTask, task.id).created_date = utc_now() - timedelta(minutes=61)
        session.commit()
    condition, reason = helper._check_start_stop(zone, repos.irrigation_task.get(task.id))
    assert condition == helper.STOP and reason.startswith("hard stop")


def test_auto_irrigation_tick_starts_then_hard_stops(repos, farm_with_zone):
    from interfaces.flow_runner.flow_runner import ZoneAutomaticIrrigationHelper as helper

    broker = RecordingBroker()
    helper.configure(_use_cases_with(repos, broker))
    _record(repos, "MSN1", "moisture", 20)
    _record(repos, "SAT1", "saturation", 30)

    helper.auto_irrigation()
    tasks = repos.irrigation_task.filter([])
    assert [t.status for t in tasks] == [global_constants.IRRIGATION_TASK_IN_PROGRESS]

    from infrastructure.database.tables.irrigation_task import IrrigationTask

    with repos.irrigation_task.Session() as session:
        session.get(IrrigationTask, tasks[0].id).created_date = utc_now() - timedelta(minutes=61)
        session.commit()
    helper.auto_irrigation()
    assert repos.irrigation_task.get(tasks[0].id).status == global_constants.IRRIGATION_TASK_COMPLETED
    assert [c["data"]["status"] for c in broker.commands] == ["On", "On", "Off"]

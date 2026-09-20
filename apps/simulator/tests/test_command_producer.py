import pytest

from actuators.command_producer import ACTUATOR_STATE, CommandProducer


class FakeProducer:
    def __init__(self):
        self.sent = []

    def produce(self, topic, key, value):
        self.sent.append((topic, key, value))

    def flush(self, timeout):
        return 0


@pytest.fixture
def producer(monkeypatch):
    monkeypatch.setattr("actuators.command_producer.Producer", lambda _config: FakeProducer())
    return CommandProducer()


def test_switch_on_confirms_with_the_actuator_table(producer):
    producer.process(
        {
            "event_type": "status_data",
            "sensor_serial_number": "SWA001",
            "data": {"type": "switcher", "status": "On", "timestamp": "x"},
        }
    )
    topic, key, value = producer.producer.sent[0]
    assert key == "sensor_new_status_data"
    assert b'"water_flow_rate": 15.2' in value and b'"status": "On"' in value
    assert ACTUATOR_STATE[("source", "Off")]["consumption"] == 1000


def test_unknown_actuator_or_status_is_rejected(producer):
    with pytest.raises(ValueError):
        producer.process(
            {"event_type": "status_data", "sensor_serial_number": "X", "data": {"type": "valve", "status": "On"}}
        )
    with pytest.raises(ValueError):
        producer.process({"sensor_serial_number": "X", "data": {}})


def test_readings_are_ignored(producer):
    producer.process({"event_type": "data_record", "sensor_serial_number": "MSN1", "data": {}})
    assert producer.producer.sent == []

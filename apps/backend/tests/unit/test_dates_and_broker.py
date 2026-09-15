from datetime import timedelta

import pytest

from common.dates import minutes_since, parse_db_datetime, utc_now
from common.exceptions import BrokerError
from infrastructure.repositories.base import BaseBrokerRepo, NoopBrokerRepo


def test_parse_db_datetime_with_and_without_microseconds():
    assert parse_db_datetime("2026-09-15 16:07:10.741427").microsecond == 741427
    assert parse_db_datetime("2026-09-15 16:07:10").second == 10


def test_minutes_since_uses_utc_not_local_time():
    ten_minutes_ago = str(utc_now() - timedelta(minutes=10))
    assert 9.9 < minutes_since(ten_minutes_ago) < 10.1


class FakeProducer:
    def __init__(self, error=None, remaining=0):
        self.error, self.remaining, self.sent = error, remaining, []

    def produce(self, topic, key, value, on_delivery):
        self.sent.append((topic, key, value))
        on_delivery(self.error, None)

    def flush(self, timeout):
        return self.remaining


def test_send_event_adds_event_type_and_delivers():
    producer = FakeProducer()
    BaseBrokerRepo(producer=producer, random_broker="b").send_event({"sensor_serial_number": "S"}, "t", "k")
    topic, key, value = producer.sent[0]
    assert (topic, key) == ("t", "k")
    assert b'"event_type": "status_data"' in value


def test_delivery_error_raises_broker_error():
    repo = BaseBrokerRepo(producer=FakeProducer(error="Broker: Unknown topic"), random_broker="b")
    with pytest.raises(BrokerError):
        repo.send_event({}, "t", "k")


def test_unacknowledged_message_raises_broker_error():
    repo = BaseBrokerRepo(producer=FakeProducer(remaining=1), random_broker="b")
    with pytest.raises(BrokerError):
        repo.send_event({}, "t", "k")


def test_noop_broker_drops_commands_without_a_producer(caplog):
    repo = NoopBrokerRepo()
    assert repo.producer is None
    with caplog.at_level("DEBUG"):
        repo.send_event({"sensor_serial_number": "S"}, "t", "k")
    assert "dropped" in caplog.text

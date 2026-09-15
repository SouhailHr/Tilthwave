"""
Sensor simulator: publishes fake zone readings to the sensors topic.

Event payload:
 {  'event_type': 'data_record',
    'sensor_serial_number': 'MSN123457',
    'data': {'type': 'moisture', 'value': 35, 'timestamp': '2024-05-17 23:29:26'}
 }

Values climb every round and wrap back to their start after CYCLE_ROUNDS rounds. The profiles
start below the demo zones' start triggers (moisture 50 / saturation 60) and end above their stop
triggers (80 / 90), so every cycle starts one irrigation and lets the backend stop it.
The process loops itself (SENSORS_ROUNDS=0): a container restart policy is for crashes.
"""

import json
import logging
import random
import time
from datetime import UTC, datetime

from confluent_kafka import Producer

from config.logging import configure_logging
from config.settings import settings
from sensors.api_client import FarmApiClient

# Sensor types in the API are suffixed with "_sensor"; the simulator only generates readings for these.
DATA_RECORD_SENSOR_TYPES = ("temperature", "moisture", "saturation")

# (start value, increment per round) per reading type
PROFILES = {
    "temperature": (20, 2),  # 20 .. 38
    "moisture": (30, 7),  # 30 .. 93
    "saturation": (35, 7),  # 35 .. 98
}

configure_logging(settings.STREAMER.LOG_LEVEL)
logger = logging.getLogger(__name__)


class ReadingPublisher:
    """One Kafka producer for the whole run (a producer per message costs ~40 ms and two threads)."""

    def __init__(self):
        self.broker = random.choice(settings.STREAMER.BROKER_HOSTS)
        self.producer = Producer({"bootstrap.servers": self.broker})

    def publish(self, event: dict):
        logger.info("Sending event: %s", event)
        self.producer.produce(
            settings.STREAMER.SENSORS_TOPIC, key="sensor_new_data_record", value=json.dumps(event).encode("utf-8")
        )
        self.producer.poll(0)

    def flush(self):
        self.producer.flush(10)


def now_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def fetch_zones_from_api() -> dict:
    """
    Build a {zone_name: {sensor_type: serial_number}} mapping by querying the API.
    Sensor type names are stripped of their "_sensor" suffix to match PROFILES.
    """
    client = FarmApiClient()
    client.login()

    sensor_type_by_serial = {s["serial_number"]: s["type"] for s in client.get_sensors()}

    zones: dict = {}
    for zs in client.get_zone_sensors():
        serial = zs["sensor_serial_number"]
        zone_name = zs["zone_name"]
        api_type = sensor_type_by_serial.get(serial)
        if not api_type:
            logger.warning("Sensor %s for zone %s missing from /sensors/ response", serial, zone_name)
            continue
        sensor_type = api_type.removesuffix("_sensor")
        if sensor_type not in DATA_RECORD_SENSOR_TYPES:
            continue
        zones.setdefault(zone_name, {})[sensor_type] = serial
    return zones


def generate_event(sensor_type, serial_number, value):
    return {
        "event_type": "data_record",
        "sensor_serial_number": serial_number,
        "data": {
            "value": value,
            "type": sensor_type,
            "timestamp": now_timestamp(),
        },
    }


def value_for(sensor_type: str, round_index: int) -> int:
    start, step = PROFILES[sensor_type]
    return start + step * (round_index % settings.SENSORS.CYCLE_ROUNDS)


def run(zones: dict, publisher: ReadingPublisher):
    rounds = settings.SENSORS.ROUNDS
    round_index = 0
    while rounds == 0 or round_index < rounds:
        for sensors in zones.values():
            for sensor_type, serial_number in sensors.items():
                if sensor_type in PROFILES:
                    publisher.publish(generate_event(sensor_type, serial_number, value_for(sensor_type, round_index)))
        publisher.flush()
        round_index += 1
        time.sleep(settings.SENSORS.INTERVAL_SECONDS)


if __name__ == "__main__":
    logger.info("................ Starting the sensor simulator .........")
    if not settings.API.PASSWORD:
        raise SystemExit("API_PASSWORD is not set; the sensor simulator needs an API login to discover zones")
    discovered_zones = fetch_zones_from_api()
    if not discovered_zones:
        logger.error("No zones returned from API; nothing to simulate")
        raise SystemExit(1)
    logger.info("Simulating %d zone(s): %s", len(discovered_zones), ", ".join(discovered_zones))
    run(discovered_zones, ReadingPublisher())

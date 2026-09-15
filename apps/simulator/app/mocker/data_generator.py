"""
A module that generate Mock data for zone sensors and send it to kafka topic.
Its take as input:
    1- event_type as record_data
    2- Zones Sensors
    3- generated values
    4- timestamp

Event payload:
 {  'event_type': 'data_record',
    'sensor_serial_number': 'MSN123457',
    'data':
      {
       'type': 'moisture',
       'value': 135,
       'timestamp': '2024-05-17 23:29:26'
      }
 }
"""
import json
import logging
import random
import time
from datetime import datetime

from config.settings import settings
from mocker.api_client import FarmApiClient

from confluent_kafka import Producer

# Sensor types in the API are suffixed with "_sensor"; the mocker only
# generates data records for these three.
DATA_RECORD_SENSOR_TYPES = ("temperature", "moisture", "saturation")

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


def push_event_to_broker(topic, key, event):
    # Kafka broker configuration
    random_broker = random.choice(settings.STREAMER.BROKER_HOSTS)

    # Create a Kafka producer
    producer = Producer({"bootstrap.servers": random_broker})

    # Encode the event as a JSON string
    event_json = json.dumps(event)

    # Produce the event to the specified topic
    logger.info(f"Pushing event {key}.{topic} on broker {random_broker}")

    producer.produce(topic, key=key, value=event_json.encode("utf-8"))
    # Flush the producer to ensure the message is sent
    producer.flush()


def get_formatted_now_date():
    # Get the current datetime.
    current_datetime = datetime.now()

    # Format the datetime as per the specified format
    return current_datetime.strftime("%Y-%m-%d %H:%M:%S")


def fetch_zones_from_api() -> dict:
    """
    Build a {zone_name: {sensor_type: serial_number}} mapping by querying
    the farm-watch-commander API. Sensor type names are stripped of their
    "_sensor" suffix to match the mocker's internal naming.
    """
    client = FarmApiClient()
    client.login()

    sensor_type_by_serial = {
        s["serial_number"]: s["type"] for s in client.get_sensors()
    }

    zones: dict = {}
    for zs in client.get_zone_sensors():
        serial = zs["sensor_serial_number"]
        zone_name = zs["zone_name"]
        api_type = sensor_type_by_serial.get(serial)
        if not api_type:
            logger.warning(
                "Sensor %s for zone %s missing from /sensors/ response",
                serial, zone_name,
            )
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
            "timestamp": get_formatted_now_date(),
        },
    }


def send_event(sensor_type, serial_number, value):
    event = generate_event(sensor_type, serial_number, value)
    # Send event to Kafka broker
    logger.info(f"Sending event: {event}")
    time.sleep(0.1)  # Simulate some delay between events
    push_event_to_broker(topic=settings.STREAMER.SENSORS_TOPIC, key="sensor_new_data_record", event=event)


def start_process(zones: dict):
    start_value_temperature = 20
    start_value_moist = 35
    start_value_saturation = 40
    for i in range(0, 10):
        for zone, sensors in zones.items():
            for sensor_type, serial_number in sensors.items():
                if sensor_type == "temperature":
                    send_event(sensor_type, serial_number, start_value_temperature)
                elif sensor_type == "moisture":
                    send_event(sensor_type, serial_number, start_value_moist)
                elif sensor_type == "saturation":
                    send_event(sensor_type, serial_number, start_value_saturation)
            # Increase the values
            start_value_temperature += 2
            start_value_moist += 5
            start_value_saturation += 5
        time.sleep(15)  # Sleep for 30 seconds after sending each set of events


if __name__ == "__main__":
    logger.debug(f"................Starting Sensor Guard mocker ......... ")
    zones = fetch_zones_from_api()
    if not zones:
        logger.error("No zones returned from API; nothing to mock")
        raise SystemExit(1)
    start_process(zones)

"""
Actuator simulator: answers water-control commands with a status confirmation.

Receives (from the backend flow runner):
{ "event_type": "status_data", "sensor_serial_number": "SWA001",
  "data": {"type": "switcher", "status": "On", "timestamp": "..."} }

Sends back on the sensors topic:
{ "event_type": "status_data", "sensor_serial_number": "SWA001",
  "data": {"type": "switcher", "water_flow_rate": 15.2, "status": "On", "timestamp": "..."} }
"""

import json
import logging
import random
from datetime import UTC, datetime

from confluent_kafka import Producer

from config.settings import settings

logger = logging.getLogger(__name__)

# What the physical actuator would report for each (type, status): table driven like the backend.
ACTUATOR_STATE = {
    ("switcher", "On"): {"water_flow_rate": 15.2},  # liters per minute
    ("switcher", "Off"): {"water_flow_rate": 0.0},
    ("source", "On"): {"water_level": 15.5, "water_capacity": 1000},  # meters, cubic meters
    ("source", "Off"): {"water_level": 0, "water_capacity": 0, "consumption": 1000},  # liters consumed
}


class CommandProducer:
    """
    Receives a command event, "applies" it, and publishes the resulting actuator status.
    """

    def __init__(self):
        self.broker = random.choice(settings.STREAMER.BROKER_HOSTS)
        self.producer = Producer({"bootstrap.servers": self.broker})

    @staticmethod
    def _extract_event_type(event):
        event_type = event.get("event_type")
        if event_type is None:
            raise ValueError("Payload missing event type")
        return event_type

    @staticmethod
    def _now_timestamp():
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M")

    def _push_event_to_broker(self, topic, key, event):
        logger.info("Pushing event %s.%s on broker %s", key, topic, self.broker)
        self.producer.produce(topic, key=key, value=json.dumps(event).encode("utf-8"))
        self.producer.flush(10)

    def _handle_command(self, event):
        """
        Build the status event confirming the command.
        @raises ValueError: unknown actuator type / status
        """
        data = event.get("data") or {}
        actuator_type, status = data.get("type"), data.get("status")
        state = ACTUATOR_STATE.get((actuator_type, status))
        if state is None:
            raise ValueError(f"Unknown command {actuator_type!r}/{status!r}")
        logger.info("Applying command: %s -> %s", actuator_type, status)
        return {
            "event_type": event.get("event_type"),
            "sensor_serial_number": event.get("sensor_serial_number"),
            "data": {"type": actuator_type, "status": status, "timestamp": self._now_timestamp(), **state},
        }

    def process(self, event):
        """
        Processing the event based on the event type
        @param event: The event data to be processed
        """
        logger.info("Command Event Received: %s", event)
        if self._extract_event_type(event) != "status_data":
            logger.debug("Ignoring event type %s", event.get("event_type"))
            return
        confirmation = self._handle_command(event)
        logger.info("Sending back event - Command: %s", confirmation)
        self._push_event_to_broker(
            topic=settings.STREAMER.SENSORS_TOPIC, key="sensor_new_status_data", event=confirmation
        )

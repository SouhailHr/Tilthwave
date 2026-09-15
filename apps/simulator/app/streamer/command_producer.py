import json
import logging
import random
import time
from datetime import datetime

from confluent_kafka import Producer
from config.settings import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class CommandProducer:
    """
    A class that receives a command event, processes it, and sends back a confirmation event
    """
    random_broker = random.choice(settings.STREAMER.BROKER_HOSTS)
    producer = Producer({"bootstrap.servers": random_broker})

    @classmethod
    def _extract_event_type(cls, event):
        event_type = event.get("event_type")
        if event_type is None:
            raise Exception("Payload missing event type")
        return event_type

    @classmethod
    def _get_current_timestamp(cls):
        """
        This method gets the current timestamp
        :return: date timestamp
        """
        current_datetime = datetime.now()
        timestamp = current_datetime.strftime("%Y-%m-%d %H:%M")
        return timestamp

    def _push_event_to_broker(self, topic, key, event):
        # Encode the event as a JSON string
        event_json = json.dumps(event)

        # Produce the event to the specified topic
        logger.info(f"Pushing event {key}.{topic} on broker {self.random_broker}")
        self.producer.produce(topic, key=key, value=event_json.encode("utf-8"))
        self.producer.flush()

    def _send_event(self, event, topic, key):
        """
        This method sends an event
        @param event: The event data to be sent
        @param topic: The Kafka topic to send the event to
        @param key: The key for partitioning in Kafka
        @return: None
        """
        event = self._handle_command(event=event)
        # Send event to Kafka broker
        logger.info(f"Sending back event - Command: {event}")
        time.sleep(0.1)  # Simulate some delay between events
        self._push_event_to_broker(topic=topic, key=key, event=event)

    def _handle_command(self, event):
        """
        This method takes an event as input, adds data to it, and returns the updated event
        @param event: The event data to be handled
        @return: The updated event
        """
        data = event.get("data")
        event_type = event.get("event_type")
        sensor_serial_number = event.get("sensor_serial_number")

        updated_event = {
            "event_type": event_type,
            "sensor_serial_number": sensor_serial_number,
            "data": {}
        }

        if data.get("type") == "switcher":
            # Update water switcher data
            logger.info("***** Sending command and data to the water switcher *****")
            if data.get("status") == "On":
                logger.info("***** Command to open water switcher *****")
                command_data = {
                    "type": data.get("type"),
                    "water_flow_rate": 15.2,  # in liters per minute
                    "status": "On",  # operational status
                    "timestamp": self._get_current_timestamp(),
                }
                updated_event["data"].update(command_data)

            elif data.get("status") == "Off":
                command_data = {
                    "type": data.get("type"),
                    "water_flow_rate": 0.0,  # in liters per minute
                    "status": "Off",  # operational status
                    "timestamp": self._get_current_timestamp(),
                }
                updated_event["data"].update(command_data)

        elif data.get("type") == "source":
            # Update water source status
            logger.info("***** Sending command and data to the water source *****")
            if data.get("status") == "On":
                logger.info("***** Command to open water source *****")
                command_data = {
                    "type": data.get("type"),
                    "water_level": 15.5,  # in meters
                    "water_capacity": 1000,  # in cubic meters
                    "status": "On",  # operational status
                    "timestamp": self._get_current_timestamp(),
                }
                updated_event["data"].update(command_data)
            elif data.get("status") == "Off":
                logger.info("***** Command to close water source *****")
                command_data = {
                    "type": data.get("type"),
                    "water_level": 0,  # in meters
                    "water_capacity": 0,  # in cubic meters
                    "consumption": 1000,  # in liters
                    "status": "Off",  # operational status
                    "timestamp": self._get_current_timestamp(),
                }
                updated_event["data"].update(command_data)

        return updated_event

    def process(self, event):
        """
        Processing the event based on the event type
        @param event: The event data to be processed
        @return: None
        """
        logger.info(f'Command Event Received: {event}')
        try:
            event_type = self._extract_event_type(event=event)
            if event_type == "status_data":
                self._send_event(event=event, topic=settings.STREAMER.SENSORS_TOPIC, key="sensor_new_status_data")
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            raise e

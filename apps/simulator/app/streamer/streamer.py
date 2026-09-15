"""
The FastStream application streams events from a Kafka queue.
This streamer subscribes to the water_control topic and listen to the commands
for water control of the water sources and switchers
when he receives an event he will answer back by sending a record data containing an event_type : status_data
containing the info of the water source or water switcher with the new updated status and new data
example :
Receives :
{
    "sensor_serial_number": WSOSEN1234,
    "event_type": "status_data",
    "type": "source",
    "data":
        {
        "status": "Off"
        "timestamp": 12/02/2024 22:42,
        },
}
SendBack :
{
    "sensor_serial_number": WSOSEN1234,
    "event_type": "status_data",
    "timestamp": 12/02/2024 22:42,
    "type": "source",
    "data":
        {
        "water_level": 0,  # in meters
        "water_capacity": 0,  # in cubic meters
        "consumption": 1000,  # in liters
        "status": "Off"
        },
}
"""

import logging

from faststream import FastStream
from faststream.confluent import KafkaBroker

from streamer.command_producer import CommandProducer
from config.settings import settings

logger = logging.getLogger(__name__)

logger.info("Starting Streamer ...")

# KafkaBroker
broker = KafkaBroker(bootstrap_servers=settings.STREAMER.BROKER_HOSTS, logger=logger)

# FastStream
fast_stream = FastStream(broker, logger=logger)

command_producer = CommandProducer()


@broker.subscriber(settings.STREAMER.WATER_CONTROL_TOPIC)
async def command_streamer(event):
    try:
        command_producer.process(event=event)
    except Exception as e:
        logger.error("Something went wrong getting the command : %s", str(e))
        raise Exception("Failed to confirm command to an error") from e

"""
The FastStream application subscribing to the water-control topic: every command published by
the backend flow runner is answered with an actuator status event (see CommandProducer).

Consumer settings are explicit (own group, replay from earliest, ack after processing) so no
command is skipped because the simulator joined the group after it was published.
"""

import logging

from faststream import FastStream
from faststream.confluent import KafkaBroker

from actuators.command_producer import CommandProducer
from config.logging import configure_logging
from config.settings import settings

configure_logging(settings.STREAMER.LOG_LEVEL)
logger = logging.getLogger(__name__)

logger.info("Starting the actuator simulator ...")

broker = KafkaBroker(bootstrap_servers=settings.STREAMER.BROKER_HOSTS, logger=logger)
fast_stream = FastStream(broker, logger=logger)

command_producer = CommandProducer()


@broker.subscriber(
    settings.STREAMER.WATER_CONTROL_TOPIC,
    group_id=settings.STREAMER.GROUP_ID,
    auto_offset_reset="earliest",
    auto_commit=False,
)
async def command_streamer(event: dict):
    try:
        command_producer.process(event=event)
    except Exception:
        logger.exception("Failed to handle command %s", event)
        raise

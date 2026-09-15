"""
The FastStream application streams events from the sensors topic into the database.

Consumer settings are explicit so behaviour does not depend on library defaults:
  - group_id: offsets are committed per application and survive restarts,
  - auto_offset_reset="earliest": a fresh group replays what was published before it joined
    (readings published while the streamer was starting are not skipped),
  - auto_commit=False: FastStream acknowledges a message only after the handler returned, so a
    failure (e.g. the database being unavailable) leaves the message to be re-consumed.
"""

import logging

from faststream import FastStream
from faststream.confluent import KafkaBroker

from common.logging import configure_logging
from config.settings import settings
from interfaces.streamer.event_handler import EventHandler

configure_logging(settings.STREAMER.LOG_LEVEL)
logger = logging.getLogger(__name__)

logger.info("Starting Streamer ...")

# KafkaBroker
broker = KafkaBroker(bootstrap_servers=settings.STREAMER.BROKER_HOSTS, logger=logger)

# FastStream
fast_stream = FastStream(broker, logger=logger)

event_handler = EventHandler()


@broker.subscriber(
    settings.STREAMER.SENSORS_TOPIC,
    group_id=settings.STREAMER.GROUP_ID,
    auto_offset_reset="earliest",
    auto_commit=False,
)
async def sensors_streamer(event: dict):
    try:
        event_handler.process(event=event)
    except Exception:
        logger.exception("Failed to process event %s", event)
        raise

"""
The FastStream application streams events from the sensors topic into the database.

Consumer settings are explicit so behaviour does not depend on library defaults:
  - group_id: offsets are committed per application and survive restarts,
  - auto_offset_reset="earliest": a fresh group replays what was published before it joined
    (readings published while the streamer was starting are not skipped),
  - auto_commit=False: FastStream acknowledges a message only after the handler returned. What
    happens when the handler raises is decided in sensors_streamer below, because the library
    default (reject) would silently lose messages during a database outage.

/health answers 204 while the broker connection responds to a ping and 500 otherwise; it is the
container healthcheck in deploy/docker-compose.yml, served by uvicorn on the --host/--port that
docker/streamer/entrypoint.sh passes to `faststream run`.
"""

import logging
import time

from faststream.asgi import AsgiFastStream, make_ping_asgi
from faststream.confluent import KafkaBroker
from faststream.exceptions import NackMessage

from common.logging import configure_logging
from config.settings import settings
from infrastructure.exceptions import DBReposException
from interfaces.streamer.event_handler import EventHandler

configure_logging(settings.STREAMER.LOG_LEVEL)
logger = logging.getLogger(__name__)

logger.info("Starting Streamer ...")

# Seconds to wait before re-consuming a message the database could not take: long enough not to
# hammer a database that is restarting, short enough that readings are stored soon after it is back.
DB_RETRY_SECONDS = 5

# KafkaBroker
broker = KafkaBroker(bootstrap_servers=settings.STREAMER.BROKER_HOSTS, logger=logger)

# FastStream
fast_stream = AsgiFastStream(
    broker,
    asgi_routes=[("/health", make_ping_asgi(broker, timeout=5.0))],
    logger=logger,
)

event_handler = EventHandler()


@broker.subscriber(
    settings.STREAMER.SENSORS_TOPIC,
    group_id=settings.STREAMER.GROUP_ID,
    auto_offset_reset="earliest",
    auto_commit=False,
)
def sensors_streamer(event: dict):
    """
    A plain `def`: FastStream runs sync handlers in a worker thread, so the synchronous
    SQLAlchemy work (insert, commit) no longer blocks the event loop that polls the broker; an
    `async def` here made every insert, and every reconnect wait, stall consumption.

    Two kinds of failure, two acknowledgements.

    With auto_commit=False FastStream rejects a message whose handler raised. For this broker a
    reject is a flag only, no seek, so the consumer moves on and the next successful message's
    commit moves the offset past the failed one: it is gone. That is right for a bad payload
    (retrying it would block the topic) and wrong for a database outage: every reading published
    while Postgres was down would be lost, including the actuator confirmations that
    close_all_water_sources relies on to know a source is open. So an infrastructure error nacks
    instead, which seeks back to this offset: the message is re-consumed until the database takes
    it, and nothing behind it is committed meanwhile.
    """
    try:
        event_handler.process(event=event)
    except DBReposException:
        logger.exception("Database unavailable; re-consuming the event in %ss", DB_RETRY_SECONDS)
        time.sleep(DB_RETRY_SECONDS)
        raise NackMessage() from None
    except Exception:
        logger.exception("Failed to process event %s; skipping it", event)
        raise

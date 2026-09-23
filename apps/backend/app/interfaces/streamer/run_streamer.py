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
docker/streamer/entrypoint.sh passes to `faststream run`. /metrics on the same port is the
process's Prometheus registry (common/metrics.py); the port stays inside the compose network.
"""

import json
import logging
import random
import time

from confluent_kafka import Producer
from faststream.asgi import AsgiFastStream, make_ping_asgi
from faststream.confluent import KafkaBroker
from faststream.exceptions import NackMessage

from common.dates import utc_now
from common.logging import configure_logging
from common.metrics import STREAMER_EVENTS, STREAMER_RETRY_DELAY, metrics_asgi
from config.settings import settings
from infrastructure.exceptions import DBReposException
from interfaces.streamer.event_handler import EventHandler

configure_logging(settings.STREAMER.LOG_LEVEL, settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

logger.info("Starting Streamer ...")

# Seconds to wait before re-consuming a message the database could not take: long enough not to
# hammer a database that is restarting, short enough that readings are stored soon after it is back.
DB_RETRY_SECONDS = 5
# Ceiling of the exponential backoff: a long outage is retried once a minute, not every 5 s.
DB_RETRY_MAX_SECONDS = 60
# Consecutive database failures since the last event that went through; drives the backoff.
_db_failures = 0

DLQ_TOPIC = settings.STREAMER.DLQ_TOPIC or f"{settings.STREAMER.SENSORS_TOPIC}.dlq"
_dlq_producer: Producer | None = None


def retry_delay(failures: int) -> float:
    """
    Seconds to wait before re-consuming, after `failures` consecutive database errors: doubling
    from DB_RETRY_SECONDS up to DB_RETRY_MAX_SECONDS, with full jitter so several consumers
    coming back from the same outage do not retry in lockstep.
    """
    ceiling = min(DB_RETRY_MAX_SECONDS, DB_RETRY_SECONDS * 2 ** max(0, failures - 1))
    return random.uniform(ceiling / 2, ceiling)


def dead_letter(event: dict, error: Exception) -> None:
    """
    Park an event the handler rejected on the dead-letter topic, with the error and when, so it
    can be inspected and replayed (scripts/replay_dlq.py) once the cause is fixed. Best effort:
    if the broker will not take it either, the event is logged in full and skipped as before.
    """
    global _dlq_producer
    record = {"event": event, "error": f"{type(error).__name__}: {error}", "failed_at": utc_now().isoformat()}
    try:
        if _dlq_producer is None:
            _dlq_producer = Producer({"bootstrap.servers": ",".join(settings.STREAMER.BROKER_HOSTS)})
        _dlq_producer.produce(DLQ_TOPIC, value=json.dumps(record, default=str).encode("utf-8"))
        if _dlq_producer.flush(5):
            raise RuntimeError("dead-letter publish not acknowledged within 5 s")
    except Exception:
        logger.exception("Could not dead-letter the event; it is skipped: %s", record)


# KafkaBroker
broker = KafkaBroker(bootstrap_servers=settings.STREAMER.BROKER_HOSTS, logger=logger)

# FastStream
fast_stream = AsgiFastStream(
    broker,
    asgi_routes=[("/health", make_ping_asgi(broker, timeout=5.0)), ("/metrics", metrics_asgi)],
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
    commit moves the offset past the failed one. That is right for a bad payload (retrying it
    would block the topic), and the payload is not lost: it is parked on the dead-letter topic
    first (dead_letter) and wrong for a database outage: every reading published
    while Postgres was down would be lost, including the actuator confirmations that
    close_all_water_sources relies on to know a source is open. So an infrastructure error nacks
    instead, which seeks back to this offset: the message is re-consumed until the database takes
    it, with exponential backoff and jitter (retry_delay), and nothing behind it is committed
    meanwhile.
    """
    global _db_failures
    try:
        event_handler.process(event=event)
    except DBReposException:
        _db_failures += 1
        delay = retry_delay(_db_failures)
        STREAMER_EVENTS.labels("nacked").inc()
        STREAMER_RETRY_DELAY.set(delay)
        logger.exception("Database unavailable (%d in a row); re-consuming the event in %.1fs", _db_failures, delay)
        time.sleep(delay)
        raise NackMessage() from None
    except Exception as error:
        STREAMER_EVENTS.labels("rejected").inc()
        logger.exception("Failed to process event %s; dead-lettering it to %s", event, DLQ_TOPIC)
        dead_letter(event, error)
        raise
    if _db_failures:
        logger.info("Database back after %d failed attempts", _db_failures)
        _db_failures = 0
        STREAMER_RETRY_DELAY.set(0)
    STREAMER_EVENTS.labels("processed").inc()

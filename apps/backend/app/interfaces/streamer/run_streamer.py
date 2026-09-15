""""
The FastStream application streams events from a Kafka queue.
"""

import logging

from faststream import FastStream
from faststream.confluent import KafkaBroker

from config.settings import settings
from interfaces.streamer.event_handler import EventHandler

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

logger.info("Starting Streamer ...")


# KafkaBroker
broker = KafkaBroker(bootstrap_servers=settings.STREAMER.BROKER_HOSTS, logger=logger)

# FastStream
fast_stream = FastStream(broker, logger=logger)


event_handler = EventHandler()


@broker.subscriber(settings.STREAMER.SENSORS_TOPIC)
async def sensors_streamer(event):
    try:
        event_handler.process(event=event)
    except Exception as e:
        logger.error("Something went wrong saving the data to the records: %s", str(e))
        raise Exception("Failed to save data due to an error") from e


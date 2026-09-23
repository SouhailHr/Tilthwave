"""
Replay the streamer's dead-letter topic onto the sensors topic, once the cause is fixed.

Every event the streamer rejected is on STREAMER_DLQ_TOPIC (default: the sensors topic +
".dlq") as {"event", "error", "failed_at"}. This reads them all from the beginning with a
throwaway consumer group, prints them, and with --apply publishes each `event` back to the
sensors topic, where the streamer takes it again. The DLQ itself is left as it is: it is the
record of what failed.

Usage (inside a backend container, e.g. the streamer):
    python /backend/app/infrastructure/scripts/replay_dlq.py            # list only
    python /backend/app/infrastructure/scripts/replay_dlq.py --apply    # republish
"""

import argparse
import json
import sys
import uuid

from confluent_kafka import Consumer, Producer

from config.settings import settings

IDLE_POLLS_BEFORE_DONE = 5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--apply", action="store_true", help="publish the events back to the sensors topic")
    args = parser.parse_args()

    brokers = ",".join(settings.STREAMER.BROKER_HOSTS)
    dlq = settings.STREAMER.DLQ_TOPIC or f"{settings.STREAMER.SENSORS_TOPIC}.dlq"
    consumer = Consumer(
        {
            "bootstrap.servers": brokers,
            "group.id": f"tilthwave-dlq-replay-{uuid.uuid4().hex[:8]}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    producer = Producer({"bootstrap.servers": brokers, "enable.idempotence": True}) if args.apply else None
    consumer.subscribe([dlq])
    seen = idle = 0
    try:
        while idle < IDLE_POLLS_BEFORE_DONE:
            message = consumer.poll(1.0)
            if message is None:
                idle += 1
                continue
            if message.error():
                print(f"error: {message.error()}", file=sys.stderr)
                continue
            idle = 0
            seen += 1
            record = json.loads(message.value())
            print(f"{record.get('failed_at')}  {record.get('error')}  {json.dumps(record.get('event'))}")
            if producer is not None:
                producer.produce(settings.STREAMER.SENSORS_TOPIC, value=json.dumps(record["event"]).encode("utf-8"))
    finally:
        consumer.close()
    if producer is not None and producer.flush(10):
        print("some events were not acknowledged by the broker", file=sys.stderr)
        return 1
    print(f"{seen} dead-lettered event(s){' republished' if producer else ''} from {dlq}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

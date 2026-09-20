# Broker

Tilthwave uses [Redpanda](https://redpanda.com) as its Kafka-compatible broker, with two topics:

| Topic | Producer | Consumer | Payload |
|---|---|---|---|
| `tilthwave.sensors.dev` | sensor simulator, actuator simulator | backend streamer | `data_record` readings and `status_data` actuator confirmations |
| `tilthwave.water-control.dev` | backend flow-runner | actuator simulator (real actuators in production) | `status_data` commands (`On`/`Off`) |

The broker, its console and the one-shot topic creation job are defined in `deploy/docker-compose.yml`
(services `redpanda`, `console`, `broker-init`). There is nothing to build in this directory; it exists
to document the messaging contract.

## Useful commands

```bash
docker exec tilthwave-redpanda rpk topic list
docker exec tilthwave-redpanda rpk topic consume tilthwave.sensors.dev --num 5
docker exec tilthwave-redpanda rpk group list                 # one group per consuming app
open http://localhost:8082                                    # Redpanda console
```

Both topics have a single partition; keep `STREAMER_WORKERS=1` unless partitions are added.

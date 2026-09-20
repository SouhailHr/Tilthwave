# Tilthwave simulator

Two processes that stand in for the farm hardware:

- **sensors** (`app/sensors`) — logs in to the API, discovers each zone's sensors, and publishes fake
  temperature / moisture / saturation readings to the sensors topic. Values climb every round and wrap
  after `SENSORS_CYCLE_ROUNDS` rounds so the backend's start and stop triggers are both exercised.
- **actuators** (`app/actuators`) — subscribes to the water-control topic and answers every command
  from the flow-runner with the status a real water source or switcher would report.

Both run as part of the full stack (`make up` at the repo root, services `sim-sensors` and `sim-actuators`).

## Configuration

Environment variables (see `.env.example`):

| Variable | Purpose |
|---|---|
| `STREAMER_BROKER_HOSTS` | JSON list of brokers, e.g. `["redpanda:29092"]` |
| `STREAMER_SENSORS_TOPIC`, `STREAMER_WATER_CONTROL_TOPIC` | topic names |
| `STREAMER_GROUP_ID` | consumer group of the actuator simulator |
| `API_BASE_URL`, `API_USERNAME`, `API_PASSWORD` | API login used to discover zones (retries while the API starts) |
| `SENSORS_ROUNDS` | rounds to publish, `0` = forever |
| `SENSORS_INTERVAL_SECONDS` | pause between rounds |

## Development

```bash
uv sync
uv run ruff check app
uv run python app/sensors/generator.py          # needs a .env or the variables above
uv run faststream run app/actuators/streamer:fast_stream
```

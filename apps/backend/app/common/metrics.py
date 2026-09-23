"""
Prometheus metrics, one registry per process.

Every process exposes the default registry: the API at GET /metrics (behind API_METRICS_TOKEN,
interfaces/api/endpoints/metrics.py), the streamer at /metrics next to its /health, the flow
runner on FLOW_RUNNER_METRICS_PORT. The metric objects live here so a use case or repository
can count without knowing which process it runs in; a process that never touches a metric
simply exports it at zero.

Counters are per process: with UVICORN_WORKERS above 1 the API's numbers would be per worker
(prometheus_client's multiprocess mode needs a shared directory; not set up).
"""

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# ---- API -----------------------------------------------------------------------------------------

HTTP_REQUESTS = Counter(
    "tilthwave_http_requests_total",
    "HTTP requests answered by the API, by method, route template and status class.",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "tilthwave_http_request_duration_seconds",
    "Time to answer an HTTP request, by method and route template.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

# ---- streamer ------------------------------------------------------------------------------------

STREAMER_EVENTS = Counter(
    "tilthwave_streamer_events_total",
    "Broker events taken off the sensors topic, by outcome: processed, nacked (database "
    "unavailable, re-consumed), rejected (bad payload, sent to the dead-letter topic).",
    ["outcome"],
)

# ---- flow runner ---------------------------------------------------------------------------------

FLOW_RUNNER_TICKS = Counter(
    "tilthwave_flow_runner_ticks_total", "Control-loop ticks, by outcome: ok or failed.", ["outcome"]
)
FLOW_RUNNER_LAST_OK = Gauge(
    "tilthwave_flow_runner_last_successful_tick_timestamp_seconds",
    "Unix time of the last tick with no failure (the heartbeat, as a number).",
)
FLOW_RUNNER_CONSECUTIVE_FAILURES = Gauge(
    "tilthwave_flow_runner_consecutive_failures", "Failed ticks in a row; the process exits at 10."
)

# ---- broker commands (the flow runner is the only sender) ---------------------------------------

FLOW_RUNNER_BREAKER_TRIPS = Counter(
    "tilthwave_flow_runner_breaker_trips_total",
    "Ticks cut short because a field command failed: the remaining zones wait for the next tick "
    "instead of each waiting out its own broker timeout.",
)
STREAMER_RETRY_DELAY = Gauge(
    "tilthwave_streamer_retry_delay_seconds",
    "Current wait before re-consuming an event the database could not take (0 when healthy).",
)

BROKER_COMMANDS = Counter(
    "tilthwave_broker_commands_total",
    "Field commands published to the broker, by topic and outcome (sent or failed).",
    ["topic", "outcome"],
)


def render() -> tuple[bytes, str]:
    """The registry in the exposition format and its content type."""
    return generate_latest(), CONTENT_TYPE_LATEST


def now() -> float:
    return time.time()


async def metrics_asgi(scope, receive, send):
    """A minimal ASGI app answering GET with the registry: for processes without a router."""
    body, content_type = render()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", content_type.encode()), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})

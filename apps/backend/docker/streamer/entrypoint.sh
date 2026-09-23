#!/bin/bash
# Streamer: consumes the sensors topic into the database.
set -euo pipefail

echo "*********************** RUNNING THE STREAMER ************************"
# One worker per topic partition; the sensors topic has one. Never set this above the partition
# count, and never above 1 with the health endpoint: every worker would bind the same port.
# --host/--port go to uvicorn, which serves /health (the container healthcheck) and /metrics
# (run_streamer.py). 0.0.0.0 so a scraper on the compose network reaches it; the port is not
# published outside that network.
exec faststream run interfaces.streamer.run_streamer:fast_stream \
    --workers "${STREAMER_WORKERS:-1}" --host 0.0.0.0 --port 8081

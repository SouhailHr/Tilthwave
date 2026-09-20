#!/bin/bash
# Streamer: consumes the sensors topic into the database.
set -euo pipefail

echo "*********************** RUNNING THE STREAMER ************************"
# One worker per topic partition; the sensors topic has one. Never set this above the partition count.
exec faststream run interfaces.streamer.run_streamer:fast_stream --workers "${STREAMER_WORKERS:-1}"

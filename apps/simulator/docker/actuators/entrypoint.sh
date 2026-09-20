#!/bin/sh
# Actuator simulator: answers water-control commands on the broker.
set -eu

echo "*********************** RUNNING THE ACTUATOR SIMULATOR ************************"
# One worker per topic partition; the water-control topic has one.
exec faststream run app/actuators/streamer:fast_stream --workers "${STREAMER_WORKERS:-1}"

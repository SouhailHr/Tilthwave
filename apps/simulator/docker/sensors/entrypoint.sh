#!/bin/sh
# Sensor simulator: publishes fake zone readings, forever (SENSORS_ROUNDS=0).
set -eu

echo "*********************** RUNNING THE SENSOR SIMULATOR ************************"
exec python app/sensors/generator.py

#!/bin/bash
# Flow runner: the irrigation control loop.
set -euo pipefail

echo "*********************** RUNNING THE FLOW RUNNER ************************"
exec python app/interfaces/flow_runner/flow_runner.py

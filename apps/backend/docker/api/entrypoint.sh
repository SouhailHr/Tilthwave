#!/bin/bash
# API service. Migrations run in the dedicated `migrate` service (deploy/docker-compose.yml);
# set RUN_MIGRATIONS=1 to run them here instead (single-container setups).
set -euo pipefail

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
fi

echo "Starting FastAPI server..."
# UVICORN_RELOAD=1 is for a bind-mounted development checkout only.
if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
  exec uvicorn interfaces.api.main:app --host 0.0.0.0 --port 8080 --reload --reload-dir /backend/app
fi
exec uvicorn interfaces.api.main:app --host 0.0.0.0 --port 8080 \
  --workers "${UVICORN_WORKERS:-2}" --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  --timeout-graceful-shutdown 15

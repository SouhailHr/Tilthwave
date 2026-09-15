#!/bin/bash
# One-shot: apply migrations, then exit. Every other service waits for this to complete
# (service_completed_successfully), so nothing ever runs against a half-migrated schema.
set -euo pipefail

echo "Applying database migrations..."
alembic upgrade head
echo "Migrations applied."

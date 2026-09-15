#!/bin/bash

# Migrate changes the database
echo "Applying database migrations..."
alembic upgrade head

# Start server
echo "Starting FastAPI server..."
uvicorn app.interfaces.api.main:app --host 0.0.0.0 --port 8080 --reload

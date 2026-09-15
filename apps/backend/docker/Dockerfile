# syntax=docker/dockerfile:1.7
# Tilthwave backend image — one image, four entrypoints (docker/{migrate,api,streamer,flow_runner}).
FROM python:3.12-slim

WORKDIR /backend

# curl: container healthcheck. Database dumps run in the db container (make db-dump).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home-dir /backend --shell /usr/sbin/nologin app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/backend/.venv

# Dependencies first (cached layer), from the lockfile only. uv is mounted for the build step
# only, so the runtime image does not carry the 60 MB binary.
COPY pyproject.toml uv.lock ./
RUN --mount=from=ghcr.io/astral-sh/uv:0.11.21,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Project files
COPY --chown=app:app app/ app/
COPY --chown=app:app alembic/ alembic/
COPY --chown=app:app alembic.ini alembic.ini
COPY --chown=app:app docker/ docker/
RUN chmod +x docker/*/entrypoint.sh

ENV PATH="/backend/.venv/bin:$PATH" \
    PYTHONPATH=/backend/app

USER app

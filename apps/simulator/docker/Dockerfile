# syntax=docker/dockerfile:1.7
# Tilthwave simulator image — two entrypoints (docker/{sensors,actuators}).
FROM python:3.12-slim

WORKDIR /simulator

RUN groupadd --system app && useradd --system --gid app --home-dir /simulator --shell /usr/sbin/nologin app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/simulator/.venv

# Dependencies first (cached layer), from the lockfile only; uv only mounted at build time.
COPY pyproject.toml uv.lock ./
RUN --mount=from=ghcr.io/astral-sh/uv:0.11.21,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Project files. Configuration comes from environment variables (STREAMER_*, API_*, SENSORS_*).
COPY --chown=app:app app/ app/
COPY --chown=app:app docker/ docker/
RUN chmod +x docker/*/entrypoint.sh

ENV PATH="/simulator/.venv/bin:$PATH" \
    PYTHONPATH=/simulator/app

USER app

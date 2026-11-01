# syntax=docker/dockerfile:1.7
# Tilthwave backend image — one image, four entrypoints (docker/{migrate,api,streamer,flow_runner}).

# 1. Resolve and install the locked dependencies into a virtualenv. uv, its cache and the lock
#    file stay in this stage; only the finished .venv is copied out.
FROM python:3.15-slim AS builder
WORKDIR /backend
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/backend/.venv
COPY pyproject.toml uv.lock ./
RUN --mount=from=ghcr.io/astral-sh/uv:0.11.21,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# 2. Runtime: the interpreter, curl for the container healthcheck, the virtualenv and the code.
FROM python:3.15-slim
WORKDIR /backend

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home-dir /backend --shell /usr/sbin/nologin app

COPY --from=builder /backend/.venv /backend/.venv
COPY --chown=app:app app/ app/
COPY --chown=app:app alembic/ alembic/
COPY --chown=app:app alembic.ini alembic.ini
COPY --chown=app:app docker/ docker/
RUN chmod +x docker/*/entrypoint.sh

ENV PATH="/backend/.venv/bin:$PATH" \
    PYTHONPATH=/backend/app

USER app

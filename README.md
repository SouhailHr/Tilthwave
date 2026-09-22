# Tilthwave

Smart-irrigation IoT platform. A full control loop — sensors → broker → backend →
automated irrigation — with a live web dashboard. Runs as a 24/7 public demo at
`tilthwave.hannibyte.com` with a demo account and a simulated farm.

## Monorepo layout

| Path | What it is | Stack |
|---|---|---|
| `apps/backend` | API, streamer, and flow-runner services | FastAPI · FastStream · SQLAlchemy · Alembic · Postgres |
| `apps/web` | Web dashboard | Next.js 16 · React 19 · TanStack Query · shadcn/ui |
| `apps/simulator` | Sensor and actuator simulators | Python · FastStream |
| `apps/broker` | Message broker contract (Redpanda/Kafka) | Redpanda |
| `deploy` | Root compose, env template, secret generation | Docker Compose |
| `docs` | Project docs index and the [backlog](docs/BACKLOG.md) | Markdown |

## Backend services

- **Streamer** — consumes sensor data from the broker in real time and persists it.
- **API** — FastAPI REST endpoints with RBAC, per-farm tenancy, and cookie or bearer sessions.
- **Flow Runner** — evaluates real-time data and drives irrigation via the broker.

## Quick start (whole stack, one command)

Requires Docker with Compose v2.

```bash
make env       # creates deploy/.env with generated secrets (prints where the admin password is)
make up        # builds and starts everything in the background
make logs      # follow logs (make logs s=api for one service)
make test      # backend tests (SQLite) + simulator lint
```

| What | Where |
|---|---|
| Web dashboard | http://localhost:3000 (login: `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `deploy/.env`) |
| API docs | http://localhost:8080/docs |
| Redpanda console | http://localhost:8082 |
| Postgres | `localhost:5432` (`make psql`) |

On first start the stack runs migrations, seeds a demo farm (two zones, sensors, an admin
user), then the simulator logs in, publishes fake readings, and the flow-runner starts and stops
irrigation from the zone triggers. `make down` stops it (data kept); `make reset` wipes the volumes.
Host ports bind to `127.0.0.1` only; set `BIND_ADDR` in `deploy/.env` to change that.

"Forgot password" works locally without a mail server: with `SMTP_HOST` blank the API logs the
reset link instead of sending it (`make logs s=api`).

## Per-app development

Python apps use `pyproject.toml` + `uv.lock`:

```bash
cd apps/backend && uv sync && uv run ruff check app && uv run pytest -q   # same for apps/simulator
cd apps/web && npm install && npm run dev
```

Individual services can be run in isolation with the same compose file, e.g.
`docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d db redpanda api`.

## Documentation

Each app has its own README; `docs/README.md` indexes them, and `docs/BACKLOG.md` lists what is
left to do per area. `CLAUDE.md` describes the security-assessment loop used on this repo.

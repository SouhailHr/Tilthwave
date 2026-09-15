# Tilthwave

Smart-irrigation IoT platform. A full control loop — sensors → broker → backend →
automated irrigation — with a live web dashboard. Runs as a 24/7 public demo at
`tilthwave.hannibyte.com` with a demo account and a simulated farm.

## Monorepo layout

| Path | What it is | Stack |
|---|---|---|
| `apps/backend` | API, streamer, and flow-runner services | FastAPI · FastStream · SQLAlchemy · Alembic · Postgres |
| `apps/web` | Web dashboard | Next.js 16 / React |
| `apps/simulator` | Sensor simulator (SensorsGuardSandbox) | Python |
| `apps/broker` | Message broker config (Redpanda/Kafka) | Redpanda |
| `docs` | Project documentation | (cloned separately — see `docs/README.md`) |
| `deploy` | Root compose, reverse proxy, env templates | Docker Compose · Caddy/Traefik |

## Backend services

- **Streamer** — consumes sensor data from the broker in real time and persists it.
- **API** — FastAPI REST endpoints with RBAC and per-farm object authorization.
- **Flow Runner** — evaluates real-time data and drives irrigation via the broker.

## Quick start (per app)

Each app has its own README and Docker setup:

```bash
# backend (API + streamer + flow-runner + Postgres)
cd apps/backend && cp .env.example .env   # fill in secrets, then:
make up        # or: docker compose up

# web
cd apps/web && npm install && npm run dev

# simulator / broker
cd apps/simulator && docker compose up
cd apps/broker && docker compose up
```

For the full stack together, see `deploy/`.

## Documentation

Project docs live in `docs/` — clone them per `docs/README.md`.

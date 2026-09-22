# Tilthwave backend

One Python package, three processes, one image. FastAPI · FastStream · SQLAlchemy · Alembic ·
Postgres. Python 3.12, managed with `uv`.

| Process | Entry point | Role |
|---|---|---|
| **API** | `docker/api`, `interfaces.api.main:app` | REST endpoints, auth, RBAC, per-farm tenancy |
| **Streamer** | `docker/streamer` | Consumes the sensors topic, persists readings and actuator confirmations |
| **Flow runner** | `docker/flow_runner` | Every `FLOW_RUNNER_MINUTES`, evaluates each zone's latest readings against its triggers and publishes `On`/`Off` commands |
| **migrate** | `docker/migrate` | One-shot `alembic upgrade head`, run before the others |

The backend runs as part of the full stack (`make up` at the repo root). Everything below is for
working on it directly.

## Development

```bash
uv sync                      # .venv from uv.lock
uv run ruff check app tests  # lint (blocking in CI)
uv run pytest -q             # tests run on SQLite, no services needed
```

Modules are imported with `PYTHONPATH=app` (`from core.use_cases...`). To run one process on the
host against the docker stack:

```bash
cp .env.example .env         # POSTGRES_HOST=localhost, real API_SECRET_KEY (>= 32 chars)
PYTHONPATH=app uv run uvicorn interfaces.api.main:app --reload --port 8080
```

Migrations: `make migrate` / `make migration-create m="..."` at the repo root. CI runs
`alembic upgrade head`, `alembic check` (models must match the migrations) and a full downgrade.

## Layout

```
app/
  config/settings.py          pydantic-settings, one class per env prefix
  common/                     exceptions, tenant ContextVar, shared helpers
  core/                       domain: entities, use cases, security (passwords, fingerprints)
  adapters/                   SQLAlchemy model <-> domain entity mappers, one per resource
  infrastructure/             SQLAlchemy tables, repositories, Kafka gateway, mailer
  interfaces/api/             FastAPI app, endpoints, middleware, helpers
  interfaces/streamer/        FastStream subscribers
  interfaces/flow_runner/     the control loop
  wiring.py                   composition root
alembic/                      migrations
docker/                       the four entry points
tests/                        pytest, SQLite
```

## Architecture

- `wiring.py` builds repositories and use cases once per process. Only the flow runner gets a real
  Kafka gateway (`worker_use_cases`); the API and tests get a no-op one.
- **Tenancy.** `TenantContextMiddleware` resolves the caller's farm into a ContextVar; every
  repository declares a `TENANT_SCOPE` (`("column", "farm_name")`, `("self", ...)`, `("via_zone",)`,
  `("via_sensor",)`) and `BaseRepository` applies it to every query. There is no role-based
  bypass: an authenticated caller with no farm gets empty results on scoped repositories, and
  non-HTTP callers (flow runner, streamer, scripts) run unscoped. `without_tenant()` is the
  explicit escape hatch, used only for the caller's own account (profile, password), where the
  row is the caller's by construction and a farm-less bootstrap admin must still reach it.
- **Authorization.** `RBACMiddleware` checks role × method × resource before the endpoint runs.
- **Errors.** Domain exceptions (`common/exceptions.py`) become HTTP responses in one place,
  `interfaces/api/helpers/errors.py`; endpoints never build error bodies.
- **Flow runner safety.** Commands are published before task state is persisted, and two limits
  apply: `FLOW_RUNNER_MAX_IRRIGATION_MINUTES` (a task is stopped regardless of readings) and
  `FLOW_RUNNER_MAX_READING_AGE_MINUTES` (stale readings never start irrigation). A tick with any
  failure leaves the heartbeat file stale (the container healthcheck); ten failing ticks in a row
  stop the scheduler and end the process with exit code 1, so the restart policy takes over
  (`ControlLoop` in `flow_runner.py`; a `sys.exit` inside the job would be swallowed by APScheduler).
- **Streamer acknowledgements.** Offsets are committed only after the handler returned. A database
  error nacks the message (seek back, retry after `DB_RETRY_SECONDS`) so an outage loses nothing;
  a bad payload is rejected and skipped. `/health` on port 8081 (inside the container) pings the
  broker and is the compose healthcheck.
- **Lists** are newest-first by default (`order_by=id desc`), paginated with `page` / `size`.

## Authentication

Two ways to present the same JWT; the API accepts either on every request.

- **Bearer** (`Authorization: Bearer ...`) for API clients and the simulator: `POST /auth/login`
  with a JSON body `{"username", "password"}` returns the token.
- **Cookie** for the browser: `POST /auth/login` with `use_cookie=true` sets `tw_access`
  (httpOnly, `SameSite=Lax`, `Secure` when `API_COOKIE_SECURE`) and `tw_csrf` (readable). Every
  non-safe request from the cookie session must echo `tw_csrf` in `X-CSRF-Token` (double-submit),
  including `/auth/*`. `POST /auth/logout` clears both. `GET /auth/me` is the session probe the
  web app uses; it returns 401, never a redirect.

The token carries `pfp`, a 16-char fingerprint of the password hash. Changing or resetting a
password changes `pfp`, which invalidates every existing session for that user at the next
request. Password-reset tokens are separate JWTs (`purpose=password_reset`, 30 minutes) and are
refused as session tokens.

Login and forgot/reset password are rate-limited per client IP, in separate windows
(`API_LOGIN_RATE_LIMIT_PER_MINUTE`, in-process per worker; keep `UVICORN_WORKERS=1` or limit at
the proxy). The client IP is the TCP peer unless it is in `API_TRUSTED_PROXIES`, in which case
`X-Forwarded-For` is used. Unknown usernames are verified against a fixed hash so the response
time does not reveal whether the account exists.

## Endpoints

Interactive docs at `/docs` when `API_DOCS_ENABLED=true` (the compose stack sets it; the default
is off).

| Prefix | Notes |
|---|---|
| `/auth` | `login`, `logout`, `me`, `password/forgot`, `password/reset`, `token/verify/` |
| `/account` | `GET/PATCH profile`, `POST password` (own account, current password required) |
| `/dashboard` | `GET summary/`: counts for the dashboard cards, computed in SQL |
| `/farms`, `/zones`, `/trees`, `/sensors`, `/water-sources`, `/water-switchers`, `/irrigation-tasks`, `/users` | CRUD, paginated lists, tenant-scoped |
| `/zone-sensors`, `/sensor-records` | links and raw readings |
| `/health` | liveness, unauthenticated |

`POST /auth/password/forgot` always returns 202. When the identifier matches a user, a reset link
(`API_WEB_BASE_URL/reset-password?token=...`) is emailed via SMTP; with no `SMTP_HOST` configured
the message, link included, is written to the API log instead (`make logs s=api`).

## Configuration

All settings are read by `config/settings.py`, grouped by env prefix. A `.env` at
`apps/backend/.env` is optional; containers get everything from `deploy/docker-compose.yml`.

**Database** (`POSTGRES_`): `HOST`, `DB`, `USER`, `PASSWORD`, `PORT=5432`, or `URI` for a full
SQLAlchemy URI (tests use `sqlite:///`).

**API** (`API_`):

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | required | ≥ 32 random chars; placeholders are refused at startup |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE` | `120` | session lifetime, minutes (also the cookie `Max-Age`) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON list; credentials are allowed for these origins |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | per client IP, per worker |
| `TRUSTED_PROXIES` | `[]` | proxies whose `X-Forwarded-For` is believed |
| `DOCS_ENABLED` | `false` | serve `/docs` and `/openapi.json` |
| `COOKIE_SECURE` | `false` | `Secure` flag on session cookies; `true` behind TLS |
| `COOKIE_DOMAIN` | unset | host-only by default; `.example.com` when web and API are on different subdomains |
| `WEB_BASE_URL` | `http://localhost:3000` | where password-reset links point |

**Mail** (`SMTP_`): `HOST` (unset = log instead of send), `PORT=587`, `USER`, `PASSWORD`,
`FROM_ADDRESS=tilthwave@localhost`, `USE_TLS=true` (STARTTLS), `TIMEOUT_SECONDS=10` (settings only;
`deploy/docker-compose.yml` does not forward it yet). The prefix is `SMTP_`, not `MAIL_`: a `MAIL`
field would collide with the shell's `$MAIL`.

**Streamer** (`STREAMER_`): `BROKER_HOSTS` (JSON list, e.g. `["redpanda:29092"]`), `SENSORS_TOPIC`,
`WATER_CONTROL_TOPIC`, `GROUP_ID=tilthwave-backend-streamer`, `LOG_LEVEL=INFO`.

**Flow runner** (`FLOW_RUNNER_`): `MINUTES` (tick interval, required), `MAX_IRRIGATION_MINUTES=60`,
`MAX_READING_AGE_MINUTES=30`.

## Related

- `../broker`: topics and payload contract.
- `../simulator`: the sensors and actuators the streamer and flow runner talk to.
- `../../docs/BACKLOG.md`: what is left to do here.

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
uv run ruff check app tests  # lint (blocking in CI); PLC0415 keeps every import at module top
uv run pytest -q             # tests run on SQLite, no services needed
```

Modules are imported with `PYTHONPATH=app` (`from core.use_cases...`). To run one process on the
host against the docker stack:

```bash
cp .env.example .env         # POSTGRES_HOST=localhost, real API_SECRET_KEY (>= 32 chars)
PYTHONPATH=app uv run uvicorn interfaces.api.main:app --reload --port 8080
```

Migrations: `make migrate` / `make migration-create m="..."` at the repo root. CI populates the
tables at the last pre-backfill revision, then runs `alembic upgrade head`, `alembic check` (models
must match the migrations) and a full downgrade/upgrade, so every backfill and downgrade is
exercised on real rows. `alembic/migrations/env.py` takes a session advisory lock (one runner at a
time), sets `lock_timeout = 5s` (DDL that cannot get its lock fails rather than stalling every
writer behind it; rerun when the table is quiet) and commits one transaction per revision. Any
future index on `sensor_records` goes in an `autocommit_block()` with `postgresql_concurrently=True`.

## Layout

```
app/
  config/settings.py          pydantic-settings, one class per env prefix
  common/                     exceptions, tenant ContextVar, shared helpers
  core/                       domain: entities, use cases, security (passwords, fingerprints), sessions
  adapters/                   SQLAlchemy model <-> domain entity mappers, one per resource
  infrastructure/             SQLAlchemy tables, repositories, Kafka gateway, mailer
  interfaces/api/             FastAPI app, endpoints (crud_router builds each resource's five routes), middleware, helpers
  interfaces/streamer/        FastStream subscribers
  interfaces/flow_runner/     the control loop
  wiring.py                   composition root
alembic/                      migrations
docker/                       the four entry points
tests/                        pytest, SQLite
```

## Architecture

- `wiring.py` builds repositories and use cases once per process, leaves first: a use case that
  needs another receives it there and never builds one itself. Only the flow runner gets a real
  Kafka gateway (`worker_use_cases`); the API and tests get a no-op one.
- **Tenancy.** `TenantContextMiddleware` resolves the caller's farm into a ContextVar; every
  repository declares a `TENANT_SCOPE` (`TenantScope.column("farm_name")`, `.own("farm_name")`
  for the farm table, `.via_zone()`, `.via_sensor()`; `repositories/tenancy.py`), one object that
  both filters every read and binds every write, so a scope kind cannot exist on one side only
  (a farm-scoped caller cannot create a row, including a farm, under another farm). There is no role-based
  bypass, and non-HTTP callers (flow runner, streamer, scripts) run unscoped. `without_tenant()`
  is the explicit escape hatch, used only for the caller's own account (profile, password),
  where the row is the caller's by construction.
- **Authorization.** `RBACMiddleware` checks role × method × resource before the endpoint runs
  (`common/constants.py`). Workers and engineers do not see `/users`: the staff list is for admins
  and owners; everyone's own profile is `/account`. Within `/users` the use case applies the
  hierarchy: only an **owner** creates an admin or owner, gives or takes one of those roles, or
  changes, deactivates, deletes or sets the password of one (403 otherwise); an admin manages
  workers and engineers. Nobody changes their own role or status through `/users` or deletes
  themselves (422), and the last active owner of a farm cannot be demoted, deactivated or deleted.
  The first account (`create_admin.py`, the seed) is the farm's owner, and every account belongs
  to a farm: one without cannot sign in.
- **Audit.** The `audit` logger writes one `event=...` line per login attempt (success, failure,
  locked), logout, password change, forgot and reset, session revocation, user creation, role
  change, activation, deactivation, deletion and email change, with actor, target and address,
  under the request id of the request that caused it.
- **Routes.** A resource is a `BaseCrud` subclass (adaptor, use case, identifier, hooks) and one
  `crud_router(prefix, tag, helper, Create, Update, noun=...)` call (`endpoints/base.py`): POST,
  GET page, GET one, DELETE and, with an update schema, PATCH. Only `/users` (password hashing)
  and `/account`, `/auth`, `/dashboard`, `/health` write their routes by hand.
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

Two ways to present the same JWT; the API accepts either on every request. The JWT is only half
of a session: every login opens a row in `user_sessions` and the token names it in `jti`
(`core/use_cases/user_session.py`). A request is refused, whatever the signature says, when that
row is missing, revoked, idle for more than `API_SESSION_IDLE_MINUTES` (60) or older than
`API_SESSION_MAX_HOURS` (12). So `POST /auth/logout` ends the session at once, a password change
or reset and a deactivation end every session of the user, and `/account/sessions` lists the live
ones (`DELETE /account/sessions/{id}` ends one, `DELETE /account/sessions` ends all but the
current). There is no refresh token: every request already loads the user row, so a short
stateless token would buy nothing. The algorithm is pinned to HS256 with a fixed issuer.

- **Bearer** (`Authorization: Bearer ...`) for API clients and the simulator: `POST /auth/login`
  with a JSON body `{"username", "password"}` returns `{"token", "token_type": "bearer",
  "expires_in"}`. The cookie channel returns the same shape with `token: null`.
- **Cookie** for the browser: `POST /auth/login` with `use_cookie=true` sets `tw_access`
  (httpOnly, `SameSite=Lax`, `Secure` when `API_COOKIE_SECURE`) and `tw_csrf` (readable). Every
  non-safe request from the cookie session must echo `tw_csrf` in `X-CSRF-Token` (double-submit),
  including `/auth/*`. `POST /auth/logout` clears both. `GET /auth/me` is the session probe the
  web app uses; it returns 401, never a redirect.

Password-reset tokens are separate JWTs (`purpose=password_reset`, 30 minutes) carrying a
fingerprint of the current password hash, so a link is single-use; they are refused as session
tokens.

Login and forgot/reset password are rate-limited per client IP, in separate windows
(`API_LOGIN_RATE_LIMIT_PER_MINUTE`, in-process per worker; keep `UVICORN_WORKERS=1` or limit at
the proxy). An account is also locked after `API_LOGIN_FAILURES_PER_ACCOUNT` (5) wrong passwords
in `API_LOGIN_FAILURE_WINDOW_MINUTES` (15) from any addresses (429 until the window slides; a
successful login clears the count). The client IP is the TCP peer unless it is in `API_TRUSTED_PROXIES`, in which case
the rightmost `X-Forwarded-For` hop that is not a trusted proxy is used (a client cannot pick
its own bucket by prepending addresses). Unknown usernames are verified against a fixed hash so the response
time does not reveal whether the account exists.

## Endpoints

Interactive docs at `/docs` when `API_DOCS_ENABLED=true` (on in the local compose override, off in
the production file and by default).

Every response carries `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and
`Cache-Control: no-store`.

Errors use one envelope, `{"detail", "error_code", "request_id"}`: the message is for people, the
code (`not_found`, `conflict`, `invalid_filter`, `unprocessable`, `validation_error`,
`bad_request`, `broker_unavailable`, `unauthenticated`, `csrf`, `forbidden`, `rate_limited`,
`database_unavailable` (503 with `Retry-After: 5`), `internal_error`) is what a client branches on, and the id is on the
`X-Request-ID` response header and on every log line written while handling that request (send
your own `X-Request-ID` to have it echoed). A request-validation failure (422,
`validation_error`) adds `fields: {<field>: [<message>, ...]}`. Request bodies are closed: an
unknown field is a 422, on every create, update and auth schema. Success bodies that carry a
sentence use `message`, never `detail`. Timestamps are ISO 8601 with an explicit UTC offset
(`2026-09-15T16:06:56.266864+00:00`).

URL shape is part of the contract: collections end with a slash (`/zones/`), items do not
(`/zones/1`), and a mismatch is a 404, never a redirect (`redirect_slashes=False`).

| Prefix | Notes |
|---|---|
| `/auth` | `login`, `logout`, `me`, `password/forgot`, `password/reset` |
| `/account` | `GET/PATCH profile` (a new email needs `current_password`), `POST password` (current password required), `GET/DELETE sessions[/{id}]` |
| `/dashboard` | `GET summary/`: counts for the dashboard cards, computed in SQL |
| `/farms`, `/zones`, `/trees`, `/sensors`, `/water-sources`, `/water-switchers`, `/irrigation-tasks`, `/users` | CRUD, paginated lists, tenant-scoped |
| `/zone-sensors`, `/sensor-records` | links and raw readings |
| `/health`, `/health/ready` | liveness (process up; the container healthcheck) and readiness (`SELECT 1`, 503 when the database is unreachable); unauthenticated |
| `/metrics` | the Prometheus registry (`common/metrics.py`), bearer `API_METRICS_TOKEN`; the streamer and flow runner serve theirs on their own ports (see `deploy/README.md`) |

`POST /auth/password/forgot` always returns 202. When the identifier matches a user, a reset link
(`API_WEB_BASE_URL/reset-password?token=...`) is emailed via SMTP; with no `SMTP_HOST` configured
the message, link included, is written to the API log instead (`make logs s=api`), unless
`API_COOKIE_SECURE=true` (a TLS deployment), where a live reset link has no place in the logs and
the mail is dropped with an error line instead.

## Configuration

All settings are read by `config/settings.py`, grouped by env prefix. A `.env` at
`apps/backend/.env` is optional; containers get everything from `deploy/docker-compose.yml`.

**Database** (`POSTGRES_`): `HOST`, `DB`, `USER`, `PASSWORD`, `PORT=5432`, or `URI` for a full
SQLAlchemy URI (tests use `sqlite:///`).

**API** (`API_`):

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | required | ≥ 32 random chars; placeholders are refused at startup |
| `SESSION_IDLE_MINUTES` | `60` | a session ends after this long without a request |
| `SESSION_MAX_HOURS` | `12` | and this long after login whatever the activity (also the cookie `Max-Age`) |
| `LOGIN_FAILURES_PER_ACCOUNT` | `5` | wrong passwords per account before a 429, in `LOGIN_FAILURE_WINDOW_MINUTES` (`15`) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON list; credentials are allowed for these origins |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | login attempts per client IP, per worker |
| `TRUSTED_PROXIES` | `[]` | proxies whose `X-Forwarded-For` is believed, as addresses or networks (`["10.0.1.0/24"]`); behind a TLS proxy this must name it, or every client shares one rate-limit bucket (the API warns at startup) |
| `DOCS_ENABLED` | `false` | serve `/docs` and `/openapi.json` (the local compose override turns them on; the production file leaves them off) |
| `COOKIE_SECURE` | `false` | `Secure` flag on session cookies; `true` behind TLS |
| `COOKIE_DOMAIN` | unset | host-only by default; `.example.com` when web and API are on different subdomains |
| `WEB_BASE_URL` | `http://localhost:3000` | where password-reset links point |
| `METRICS_TOKEN` | unset | bearer token for `GET /metrics`; unset, the endpoint is a 404 |

**Mail** (`SMTP_`): `HOST` (unset = log instead of send), `PORT=587`, `USER`, `PASSWORD`,
`FROM_ADDRESS=tilthwave@localhost`, `USE_TLS=true` (STARTTLS), `TIMEOUT_SECONDS=10` (settings only;
`deploy/docker-compose.yml` does not forward it yet). The prefix is `SMTP_`, not `MAIL_`: a `MAIL`
field would collide with the shell's `$MAIL`.

**Streamer** (`STREAMER_`): `BROKER_HOSTS` (JSON list, e.g. `["redpanda:29092"]`), `SENSORS_TOPIC`,
`WATER_CONTROL_TOPIC`, `GROUP_ID=tilthwave-backend-streamer`, `LOG_LEVEL=INFO`.

**Flow runner** (`FLOW_RUNNER_`): `MINUTES` (tick interval, required), `MAX_IRRIGATION_MINUTES=60`,
`MAX_READING_AGE_MINUTES=30`, `METRICS_PORT=8082` (0 disables the metrics server).

**Process** (no prefix): `LOG_LEVEL=INFO`, `LOG_FORMAT=text|json` (`common/logging.py`).

## Related

- `../broker`: topics and payload contract.
- `../simulator`: the sensors and actuators the streamer and flow runner talk to.
- `../../docs/BACKLOG.md`: what is left to do here.

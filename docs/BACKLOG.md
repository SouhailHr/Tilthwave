# Backlog

Open work only, per area, verified against the code on 2026-09-23. Items marked **[A]** come
from the 2026-09-22 assessment (design-patterns inventory, API contracts, migrations, security,
tech debt, style, test health, performance, dependencies, production readiness). Anything fixed
is removed from this file, not struck through; git history has the rest.

## Web (`apps/web`)

- **Farm map.** The farm page was meant to carry a Leaflet map of the zones (`react-leaflet`).
  Not installed, no map. The only unfinished item of the original plan.
- **Response validation.** Only `/auth/me` is Zod-parsed; the login body is discarded and the
  profile and every entity list are hand-typed and trusted. The decision behind it (OpenAPI codegen
  vs hand-written types) is open.
- **Telemetry.** `ObservabilitySink` logs and toasts; no vendor (Sentry, PostHog), no
  `window.onerror` / `unhandledrejection`. Pick a vendor first; every API error now carries a
  `request_id` to send along.
- **Reliability knobs.** No mutation retry policy or backoff, no optimistic updates, no offline
  detection.
- **[A] Bundle.** The login route's first load is 851 KB uncompressed / 264 KB gz after the zod
  namespace import (2026-09-23; was 1 137 KB / 317 KB). The sign-in, forgot and reset pages use
  react-query and zod themselves, so `QueryProvider` cannot leave the root layout. Next: audit
  base-ui's share; `zod/mini` would be a schema-syntax migration for a smaller gain.
- **Dashboard shell.** `(app)/page.tsx` is a ~230-line client component. **[A]** Already one
  query plus pure helpers; the RSC split buys little. Low priority.
- **Env.** `NEXT_PUBLIC_API_BASE_URL` is not validated at build time (the release workflow
  refuses to build without it; `next build` itself does not).
- **Tests: still untested** after the page tests (2026-09-23): the app shell, the dashboard and
  the resource pages' column and field configs, `SensorCrudHelper` beyond the covered paths.

## Backend (`apps/backend`)

Data and migrations

- **Sensor records: retention, JSONB, partitioning, dedupe. Decision deferred (2026-09-23) until
  the first non-demo farm is sized.** At demo volume (~24k rows/week, ~1.2M a year, a few hundred
  MB) nothing here bites within a year. The questions to answer before then, with the defaults that
  would be taken: (1) how long raw readings must exist and who reads them (default: raw 90 days,
  monthly consumption rolled up forever; an hourly rollup if history charts are wanted); (2) the
  fleet and cadence to size for (default: 50 zones at one reading a minute, ~20M live rows);
  (3) partitioning (default: none, retention bounds the table; monthly partitions if raw is kept
  forever); (4) JSON → JSONB (default: convert, one `ALTER` while small; a rewrite under an
  exclusive lock later); (5) what a duplicate is, for the at-least-once streamer (default: a
  producer-side `event_id` with a unique index and a skipped `IntegrityError`; keying on
  `(sensor, timestamp)` is wrong while confirmations carry minute precision). The `%H:%M:%S` vs
  `%H:%M` timestamp mismatch between the sensor and actuator simulators is normalised in the same
  change.
- **[A] `ON UPDATE CASCADE` from `sensor.serial_number` into `sensor_records`**: renaming a serial
  rewrites every record row. Make `serial_number` read-only in the repo, or accept and document.
- **Concurrent edits.** PATCH has no `ETag` / `If-Match`; two admins editing the same row is
  last-write-wins.
- **Natural keys.** Zones, farms and sensors are referenced by name / serial rather than surrogate
  ids, so a rename cascades through the links. A design decision, not a bug.

Operations

- **Observability, what is left**: Grafana Cloud through Alloy is wired (2026-09-23, opt-in
  profile; rules and dashboard in `deploy/grafana/`). Still open: the account and the
  `push.sh` run are yours; `db-backup` health is not a metric (a docker-health exporter would
  make it alertable); the autoheal sidecar decision (docker socket = root on the host) versus
  relying on the "process down" alert; longer metric history needs a paid tier or a Prometheus on
  the host behind the same Grafana.
- **[A] `mail.py` logs and continues after the 202**; the user never learns the reset mail
  failed. Acceptable, but it is the one true log-and-continue in the backend.
- **[A] Every command does `produce()` + `flush(5)` synchronously** (`zone.py`): a tick that
  starts many zones on a slow broker runs minutes. Kept on purpose: the publish-then-persist
  invariant needs the ack before the task row changes. One flush per zone would need the gateway
  to batch acks; revisit if ticks ever approach `FLOW_RUNNER_MINUTES`.
- **Flow runner Monostate** (`configure()` classmethods, process-global `consecutive_failures`;
  an autouse fixture resets it between tests). Making it an instance built in `run()` is the
  clean form; low interest.
- **`faststream` pinned at 0.5.48** (backend and simulator). 0.7 removed the `auto_commit`
  subscriber kwarg; the nack-on-database-error handling in `run_streamer.py` must be re-verified
  on 0.7.

Tests (behavioural, run on SQLite and on Postgres in CI, with coverage reported; gaps only)

- **No coverage threshold**: collection only; set a floor once the numbers have been read a few
  times.

Decisions recorded (not work items)

- **`Float`, not `NUMERIC`**, for farm size, tree dimensions, water pressure/volume and the
  consumption readings: they are measurements, not money. If consumption ever feeds billing, the
  sum in `SensorRecordDBRepository.monthly_consumption` and the columns move to `NUMERIC`.
- **No refresh token.** Sessions are server-side (`user_sessions`, `jti` in the token, 60 min
  idle / 12 h absolute, decided 2026-09-23): every request already loads the user row, so a short
  stateless access token plus a refresh dance would add moving parts and no security.
- **Owner over admin** (2026-09-23): only an owner appoints or removes admins and owners; the
  first account is the farm's owner; every account belongs to a farm. The audit trail is plain
  `key=value` lines on the `audit` logger until the JSON formatter and a sink exist
  (observability item above).
- **Publish-then-persist instead of an outbox.** The flow runner needs the broker's ack before a
  task row can claim a valve is open; an outbox would record the intent first. The compensating
  action for a publish that succeeded without its persist is the next tick's
  `close_all_water_sources`.

Found by the 2026-09-23 re-run, still open (the rest of that run is fixed in `fix/re-run-findings`)

- **Simulators in the production compose without a profile** (`seed`, `sim-actuators`,
  `sim-sensors`; `flow-runner` waits on `seed`). Coolify runs the demo today, so this is a
  decision: `profiles: [demo]` on the three plus `COMPOSE_PROFILES=demo` in Coolify's env, so a
  real farm cannot start with fake confirmations feeding the loop.
- **Broker down mid-irrigation leaves a valve open** (accepted physical-safety dependency): stop
  commands need the broker's ack, so the task stays in progress and the hard stop cannot reach
  the field either; the loop retries every tick and exits after ten failures. A real actuator
  needs its own watchdog (auto-close without a keep-alive); only the simulator answers today.
- **Dependabot is running** (checked 2026-09-23): weekly, all five ecosystems, 13 PRs on
  2026-09-20. It does not re-propose a version set whose grouped PR was closed unmerged (#8 for
  the backend), which is why those versions sat still; they were bumped by hand in the
  2026-09-23 debt bundle. Left to do in GitHub settings: enable automated security fixes (off
  today); `ghcr.io/astral-sh/uv` in the Dockerfiles is by tag and outside Dependabot's parser,
  so bump it by hand.
- **`c3d4e5f6a7b8`-style `SET NOT NULL`** holds ACCESS EXCLUSIVE with a full scan; on a large
  table use `ADD CONSTRAINT … CHECK (… IS NOT NULL) NOT VALID`, `VALIDATE`, then `SET NOT NULL`.
  Noted for the next revision of that shape.
- **Unit of work**: the repository opens a session per call, so a multi-step write
  (`start_irrigation`, sensor + link) spans sessions with no transaction. Publish-then-persist
  bounds the blast radius; revisit when a second multi-write use case lands.
- **Coverage gaps**: `SensorCrudHelper` create/update handlers beyond the covered paths, the SMTP
  send path in `mail.py`, the web app shell and dashboard.
- **Generic error codes**: "Not authenticated" and "Invalid or expired token" both map to
  `unauthenticated`; login failure and an invalid reset token share `bad_request`.
- **MFA**: TOTP for admin and owner, decided for a later PR (2026-09-23).

Found by the 2026-09-23 practices review (sync/async, fault tolerance, versioning, layering,
messaging reliability, CI/CD), checked against the code; what already holds is not listed.

- **No database timeouts**: SQLAlchemy has no `connect_timeout` and Postgres no
  `statement_timeout`, so one stuck query holds an API worker or a flow-runner tick indefinitely.
  Set `connect_args={"connect_timeout": 5, "options": "-c statement_timeout=15000"}` in
  `BaseDBRepo.get_engine` (longer for migrations).
- **Streamer retry has no backoff**: a database outage re-consumes the same message every
  `DB_RETRY_SECONDS` (5 s) forever. Exponential backoff with jitter and a ceiling (e.g. 5 s to
  60 s), keeping the nack, and a metric for the current delay.
- **No circuit breaker on field commands**: with the broker down every command in a tick waits
  its full 5 s flush, so a tick with many zones runs minutes. Stop sending for the rest of the
  tick after the first `BrokerError` (the next tick retries), and count it.
- **Producer idempotence off**: the flow runner's Kafka producer uses defaults; set
  `enable.idempotence=true` (implies `acks=all`) so a retried produce cannot duplicate a
  command. Redpanda runs one replica, so an acknowledged command still dies with the volume;
  accepted for a single host.
- **No dead-letter topic**: a payload the streamer cannot parse is logged and skipped. Publish
  it to `tilthwave.sensors.dlq` with the error, alert on its rate, and add a replay script.
- **No trace id across the broker**: the API's `request_id` stops at the HTTP boundary; a
  command and the confirmation it causes cannot be joined in Loki. Put a `correlation_id` in
  every command and have the actuator echo it in the confirmation.
- **API versioning undecided**: routes are unversioned (`/zones/`). Harmless while the only
  clients are our web app and simulator, deployed together; decide before the first external
  or store-installed client (a `/v1` prefix and a checked-in OpenAPI file diffed in CI so a
  breaking change fails the build).
- **Untyped responses**: lists are `Page[dict]` and items have no `response_model`, so OpenAPI
  documents no response shapes and nothing filters output at the edge (`to_public_dict` does
  it today). Typed read models per resource; unblocks the web's response validation / codegen.
- **Use cases are module globals, not dependencies**: endpoints call `api_use_cases()` at
  import time instead of `Depends(...)`, so a test cannot swap one collaborator with
  `app.dependency_overrides`. Low priority: the suite runs the real graph on SQLite and Postgres.
- **No SAST, secret scan or DAST in CI**: CI runs lint, tests, pip-audit and npm audit only.
  Add CodeQL (or Semgrep) and gitleaks on every PR, and an OWASP ZAP baseline against the local
  stack on the release workflow.
- **Deploys are not zero-downtime**: Coolify recreates the containers, so the API answers
  nothing for about a minute per release (seen on v0.2.0), and there is one replica. Document
  the rollback (re-run the release job for the previous tag, or set `TILTHWAVE_TAG` back and
  redeploy), then decide whether a health-gated rolling start is worth it for this host.
- **Migration rule not written down**: old and new containers overlap briefly during a deploy,
  so schema changes must be expand-then-contract (add, backfill, switch code, drop in a later
  release). One paragraph in the backend README next to the existing lock rules.

## Simulator (`apps/simulator`)


- **[A] Timestamp precision** differs between the sensor generator (`%H:%M:%S`) and the actuator
  responder / backend (`%H:%M`); see the JSONB item above.
- **[A] Topic and payload vocabulary** (`data_record`, `status_data`, `switcher`, `source`,
  `On`/`Off`) is hard-coded in both apps with only one test pinning it; a simulator test that
  imports the backend constants would catch drift.
- The `faststream` pin above.

## Deploy / CI (`deploy`, `.github`)


- **Base images by tag without digest** (`python:3.12-slim`, `node:22-alpine`,
  `postgres:16-alpine`, Redpanda, console). Dependabot covers the docker ecosystem, so digests
  would stay maintained. **[A]** `apps/web/Dockerfile.dev` runs `npm install` (not `ci`) at
  start, so it can rewrite the lockfile from inside the container.
- **[A] Upgradeable without blockers**: `vite` 7 → 8, `jsdom` 25 → 29 (dev-only majors). Python
  pins and transitives were refreshed on 2026-09-23 (`uv lock --upgrade`; `uv lock --check` does
  not catch drift). Still blocked upstream: ESLint 10 (Next's plugin peers, not eslint-config-next
  itself), TypeScript 7 (`typescript-eslint` peers).
- **Kafka broker TLS / auth.** Deliberately not planned (the broker is not published outside the
  compose network). Listed so it is not forgotten.

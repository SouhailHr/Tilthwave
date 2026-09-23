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
- **[A] Bundle.** Every route, including login, ships ≥ 189 KB gz of JS. Not the quick win it
  looked like: the sign-in, forgot and reset pages use react-query (their mutations) and zod (their
  forms) themselves, so `QueryProvider` cannot leave the root layout and the shared chunk is their
  own dependency. What remains is `zod/mini` in the form schemas (a schema-syntax migration) and
  auditing base-ui's share; measure with `next build` before starting.
- **Dashboard shell.** `(app)/page.tsx` is a ~230-line client component. **[A]** Already one
  query plus pure helpers; the RSC split buys little. Low priority.
- **Env.** `NEXT_PUBLIC_API_BASE_URL` is not validated at build time (the release workflow
  refuses to build without it; `next build` itself does not).
- **[A] Tests: pages are untested.** `entity-form.tsx` and `entity-table.tsx` have their first
  tests; still none for `entity-crud-page.tsx`, the login/forgot/reset/settings pages, the
  `useCreateEntity` / `useUpdateEntity` invalidation, and the `isRedirecting` guard in `client.ts`
  (two simultaneous 401s must emit `auth:expired` once). `_entity.test.ts` reaches into
  `api.interceptors.response.handlers[0]`; drive it through `api.get()` with a mocked adapter.

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

- **[A] Observability is level 2 at best**: request ids on every response and log line, but
  plain-text logs via `basicConfig`, no metrics, and healthchecks cannot trigger restarts
  (`restart: unless-stopped` fires on exit only; a failing check only shows in `docker ps`).
  Either monitor health externally or run an autoheal sidecar.
- **[A] `UVICORN_WORKERS` falls back to `2` in `docker/api/entrypoint.sh`** but `1` in compose;
  a non-compose run doubles the login rate limit.
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

Security (accepted risk)

- **[A] No server-side revocation**: a captured JWT stays valid up to 120 min after logout; only a
  password change or deactivation kills it. Accepted for the stateless design.

Tests (behavioural, run on SQLite and on Postgres in CI, with coverage reported; gaps only)

- **Web page tests**: none for `entity-crud-page.tsx`, the login/forgot/reset/settings pages, the
  `useCreateEntity` / `useUpdateEntity` invalidation, and the `isRedirecting` guard in `client.ts`.
- **No coverage threshold**: collection only; set a floor once the numbers have been read a few
  times.

Decisions recorded (not work items)

- **`Float`, not `NUMERIC`**, for farm size, tree dimensions, water pressure/volume and the
  consumption readings: they are measurements, not money. If consumption ever feeds billing, the
  sum in `SensorRecordDBRepository.monthly_consumption` and the columns move to `NUMERIC`.
- **No refresh token.** One 120-minute httpOnly session, invalidated by the password
  fingerprint; re-login after that. Shorter sessions plus rotated refresh tokens would be the
  next step if the dashboard is ever used all day on shared machines.
- **Publish-then-persist instead of an outbox.** The flow runner needs the broker's ack before a
  task row can claim a valve is open; an outbox would record the intent first. The compensating
  action for a publish that succeeded without its persist is the next tick's
  `close_all_water_sources`.

## Simulator (`apps/simulator`)

- **[A] Wrong-password retry loop.** `api_client.py` treats 400 as "admin not seeded yet" and
  the backend returns 400 for bad credentials, so a wrong `SIM_PASSWORD` retries forever,
  silently. Log the body on 400.
- **[A] Timestamp precision** differs between the sensor generator (`%H:%M:%S`) and the actuator
  responder / backend (`%H:%M`); see the JSONB item above.
- **[A] Topic and payload vocabulary** (`data_record`, `status_data`, `switcher`, `source`,
  `On`/`Off`) is hard-coded in both apps with only one test pinning it; a simulator test that
  imports the backend constants would catch drift.
- The `faststream` pin above.

## Deploy / CI (`deploy`, `.github`)

- **Coolify setup is not finished.** Resource created; still to do: DNS A records for
  `tilthwave.hannibyte.com` and `api.tilthwave.hannibyte.com`, the environment values from the
  checklist in `deploy/README.md`, the two domains on `web` and `api`, auto-deploy off,
  `docker login ghcr.io` on the server, the GitHub variables `NEXT_PUBLIC_API_BASE_URL`,
  `COOLIFY_URL`, `COOLIFY_APP_UUID` and secret `COOLIFY_TOKEN`, then the first `v0.1.0` tag.
  Nothing verifies the Coolify environment holds the production values from the checklist.
- **Base images by tag without digest** (`python:3.12-slim`, `node:22-alpine`,
  `postgres:16-alpine`, Redpanda, console). Dependabot covers the docker ecosystem, so digests
  would stay maintained. **[A]** `apps/web/Dockerfile.dev` runs `npm install` (not `ci`) at
  start, so it can rewrite the lockfile from inside the container.
- **[A] Upgradeable without blockers**: `vite` 7 → 8, `jsdom` 25 → 29 (dev-only), SQLAlchemy
  2.0.43 → 2.0.54, stale transitives (`uv lock --upgrade`; `uv lock --check` does not catch
  drift). Still blocked upstream: ESLint 10 (Next's plugin peers, not eslint-config-next itself),
  TypeScript 7 (`typescript-eslint` peers).
- **Kafka broker TLS / auth.** Deliberately not planned (the broker is not published outside the
  compose network). Listed so it is not forgotten.

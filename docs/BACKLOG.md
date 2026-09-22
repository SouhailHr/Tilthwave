# Backlog

What is known to be left, per area. Every item was checked against the code on `main` on the date
given; nothing is carried over from older audits without re-verification.

- 2026-09-22: full assessment (design-patterns inventory, API contracts, migrations, security,
  tech debt, style, test health, performance, dependencies, production readiness, AXguard,
  code review). Items marked **[A]** come from it. Library-level claims were confirmed against the
  installed versions (APScheduler 3.11, FastStream 0.5.48).
- 2026-09-22 (earlier): the backlog that replaced the May 2026 frontend documents.

Done and merged, so not listed: CI migration drift, the security round (CSRF gate before the
`/auth` exemption, cookie session, password fingerprint, login rate limit), httpOnly cookie auth
with a server-backed session, `/dashboard/summary/`, account settings and the forgot/reset
password flow, newest-first lists, full timestamps, sensor assignment, the user-menu crash.

## Fix first

Empty: the control-loop items (`fix/control-loop-safety`), the cross-tenant farm creation
(`fix/tenancy-bind-self`) and the `Idempotency-Key` decision (removed, `fix/web-contract-bugs`:
mutations never auto-retry and the form disables submit while pending, so the header only made the
contract lie) are done.

## Web (`apps/web`)

Debt

- **Farm map.** The farm page was meant to carry a Leaflet map of the zones (`react-leaflet`).
  Not installed, no map. The only unfinished item of the original plan.
- **Stringly-typed numeric form fields.** 13 fields (trees 3, water-sources 2, zones 5, farms 3)
  hold numbers as strings with a `refine`; `positiveNumber` is duplicated. **[A]** The typed field
  already exists: `EntityForm` accepts `type: "number"` and coerces (`entity-form.tsx:50,242-258`);
  no page uses it. Fix: `z.number()` + `type: "number"`, delete both `positiveNumber` copies.
- **FK picker.** Loads the referenced resource with `size: 100` and no "showing first N of M": at
  more than 100 rows it silently truncates. **[A]** Point it at `/select-list/` (no per-row
  enrichment, see backend N+1) with a longer `staleTime`; the 30 s global default already applies.
- **[A] Duplicated config across pages.** `statusOptions`/`statusVariant` (water-sources =
  water-switchers; irrigation-tasks = `recent-activity-card.tsx`), the password rule
  `min(8).max(72)` ×3 and the confirm-password refine ×2. Fix: `status-ui.ts`, shared
  `passwordSchema`.
- **[A] Dead exports.** `users.ts` `fetchUsers`/`fetchUser`/`useUsers`/`useUser`/`useDeleteUser`
  (the other seven `api/*.ts` were trimmed), `useDisclosure` `toggle`/`setOpen`; `_entity.ts` is imported by components despite the private-looking name.
- **Response validation.** Only `/auth/me` is Zod-parsed; the login body is discarded and the
  profile and every entity list are hand-typed and trusted. The decision behind it (OpenAPI codegen
  vs hand-written types) is open.
- **Telemetry.** `ObservabilitySink` logs and toasts; no vendor (Sentry, PostHog), no
  `window.onerror` / `unhandledrejection`. **[A]** The `Ref:` line in the toast reads
  `body.request_id`, which the backend never emits (see request id below).
- **Reliability knobs.** No mutation retry policy or backoff, no optimistic updates, no offline
  detection.
- **[A] Bundle.** Every route, including login, ships ≥ 189 KB gz of JS because `QueryProvider`,
  the toaster and the zod + base-ui + react-query chunk sit in the root layout. Move them to
  `(app)/layout.tsx`; consider `zod/mini` in the form schemas. Recharts is correctly code-split.
- **Dashboard shell.** `(app)/page.tsx` is a ~230-line client component. **[A]** Already one
  query plus pure helpers; the RSC split buys little. Low priority.
- **Env.** `NEXT_PUBLIC_API_BASE_URL` is not validated at build time (the release workflow
  refuses to build without it; `next build` itself does not).
- **[A] Tests: pages are untested.** `entity-form.tsx` and `entity-table.tsx` now have their
  first tests (`fix/web-contract-bugs`); still none for `entity-crud-page.tsx`, the
  login/forgot/reset/settings pages, the `useCreateEntity` / `useUpdateEntity` invalidation, and
  the `isRedirecting` guard in `client.ts` (two simultaneous 401s must emit `auth:expired` once).
  `_entity.test.ts` reaches into `api.interceptors.response.handlers[0]`; drive it through
  `api.get()` with a mocked adapter.

## Backend (`apps/backend`)

Correctness and contract

- **[A] Sensor list and detail have different shapes.** `sensor_base.py:212-218` adds
  `assigned_to` in `_enrich_item` (list path only); `GET /sensors/{id}` returns the bare row. Fix:
  enrich in `get_by_id` too.
- **[A] Two 422 shapes.** Use-case 422s carry a string `detail`, validation 422s a list, so the
  web branches on type; login stays 400 (the simulator retries on it as "admin not seeded yet").
  The envelope itself carries `error_code` and `request_id` since `chore/boundaries-and-health`.
- **[A] Success bodies reuse `detail`** (`auth.py:114`, `account.py:60,65`) and login has two
  response shapes keyed on `use_cookie`. Use `{"message"}` for success and one `LoginResponse`.
- **[A] Timestamps are `str(datetime)` of a naive UTC column** ("2026-09-15 16:06:56.266864"),
  not ISO 8601. The web compensates in `utils/dates.ts`; any new client using `Date.parse` reads
  them as local time. Fix: `d.replace(tzinfo=UTC).isoformat()` in the adapter.
- **[A] Simulator retries a wrong password forever, silently.** `api_client.py:29-47` treats 400
  as "admin not seeded yet" and the backend returns 400 for bad credentials. Log the body on 400.

Performance (`perf/set-queries` gave the repository set-oriented reads: `count_by`,
`latest_per_sensor`, `monthly_consumption`; the tick, the dashboard and the sensor list use them)

- **[A] Every command still does `produce()` + `flush(5)` synchronously** (`zone.py:290-296`): a
  tick that starts many zones on a slow broker runs minutes. Kept on purpose for now: the
  publish-then-persist invariant needs the ack before the task row changes. One flush per zone
  would need the gateway to batch acks; revisit if ticks ever approach `FLOW_RUNNER_MINUTES`.

Data and migrations

- **Sensor records grow without bound.** No retention, rollup or cleanup; ~24k rows/week from the
  simulator at 15 s rounds. `sensor_records.data` is `JSON`, not `JSONB`. **[A]** Nothing queries
  `data` in SQL today, so JSONB brings no win yet, but converting later is a full rewrite under
  `ACCESS EXCLUSIVE`; decide now (convert while cheap, or record the decision to stay). No
  partition key either, and partitioning later means recreating the table. **[A]** Three wire
  timestamp formats reach `data.timestamp` (`%H:%M:%S` from the sensor simulator, `%H:%M` from the
  actuator simulator and the backend); settle that before any JSONB migration.
- **[A] At-least-once with no dedupe.** A redelivered reading inserts a second `sensor_records`
  row; harmless for latest-reading logic, double-counts the consumption sum. A unique index on
  `(sensor_serial_number, data->>'timestamp')` once `data` is JSONB, and translate the
  `IntegrityError` to a skip.
- **[A] `ON UPDATE CASCADE` from `sensor.serial_number` into `sensor_records`**: renaming a serial
  rewrites every record row. Make `serial_number` read-only in the repo, or accept and document.
- **Concurrent edits.** PATCH has no `ETag` / `If-Match`; two admins editing the same row is
  last-write-wins.
- **Natural keys.** Zones, farms and sensors are referenced by name / serial rather than surrogate
  ids, so a rename cascades through the links. A design decision, not a bug.

Operations

- **[A] Observability is level 2 at best**: request ids on every response and log line now, but
  plain-text logs via `basicConfig`, no metrics, and healthchecks cannot trigger restarts
  (`restart: unless-stopped` fires on exit only; a failing check only shows in `docker ps`).
  Either monitor health externally or run an autoheal sidecar.
- **[A] `UVICORN_WORKERS` falls back to `2` in `docker/api/entrypoint.sh:18`** but `1` in compose;
  a non-compose run doubles the login rate limit.
- **[A] `mail.py:45-47` logs and continues after the 202**; the user never learns the reset mail
  failed. Acceptable, but it is the one true log-and-continue in the backend.

Security (Lows)

- **[A] No server-side revocation**: a captured JWT stays valid up to 120 min after logout; only a
  password change or deactivation kills it. Accepted for the stateless design.

Structure (from the design-patterns inventory; `refactor/use-case-wiring` closed the rest)

- **Flow runner Monostate** (`configure()` classmethods, process-global `consecutive_failures`).
  Tests must call `configure()` between them; add an autouse fixture that resets the class state,
  or make it an instance built in `run()`.
- **`faststream` pinned at 0.5.48** (backend and simulator). 0.7 removed the `auto_commit`
  subscriber kwarg; the nack-on-database-error handling in `run_streamer.py` must be re-verified on 0.7.

Tests (backend suite is behavioural and green: 126 tests, SQLite, real middleware; gaps only)

- **[A] Streamer `data_record` path never executed** (`event_handler.py:37-42`), nor the `source`
  branch of `status_updaters`. The highest-volume event has no test.
- **[A] Blind-zone boundaries**: exactly `MAX_READING_AGE_MINUTES`, one fresh + one stale sensor,
  saturation present but moisture missing while a task runs (must stop); two in-progress tasks.
- **[A] Routes with no HTTP test**: `/water-sources`, `/water-switchers` GET/PATCH/DELETE, `/irrigation-tasks`, `/zone-sensors`.
- **[A] Password *reset* invalidating live sessions is untested** (only change-password is).
- **[A] Postgres never runs the tests**; SQLite does not enforce FKs by default, so every
  FK-violation → 409 path behaves differently in production. The migrations job already has a
  Postgres service.

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

## Deploy / CI (`deploy`, `.github`)

- **[A] No coverage collection anywhere** (no `pytest-cov`, no `@vitest/coverage-v8`).
- **Production profile.** Production is Coolify (`deploy/README.md`): its Traefik is the TLS
  proxy, its environment is the prod profile, `db-backup` is the backup schedule, HSTS is sent by
  the apps. Still open: nothing verifies the Coolify environment holds the production values from
  the checklist.
- **Base images by tag without digest**
  (`python:3.12-slim`, `node:22-alpine`, `postgres:16-alpine`, Redpanda, console). Dependabot
  covers the docker ecosystem, so digests would stay maintained. **[A]** `apps/web/Dockerfile.dev`
  runs `npm install` (not `ci`) at start, so it can rewrite the lockfile from inside the container.
- **[A] Upgradeable without blockers**: `vite` 7 → 8, `jsdom` 25 → 29 (dev-only), SQLAlchemy
  2.0.43 → 2.0.54, stale transitives (`uv lock --upgrade`; `uv lock --check` does not catch
  drift). Still blocked upstream: ESLint 10 (Next's plugin peers, not eslint-config-next itself),
  TypeScript 7 (`typescript-eslint` peers).
- **Kafka broker TLS / auth.** Deliberately not planned (the broker is not published outside the
  compose network). Listed so it is not forgotten.

## Simulator (`apps/simulator`)

- **[A]** Wrong-password retry loop (see Backend, correctness) and the `%H:%M` vs `%H:%M:%S`
  timestamp split with the sensor generator.
- **[A]** The topic and payload vocabulary (`data_record`, `status_data`, `switcher`, `source`,
  `On`/`Off`) is hard-coded in both apps with only one test pinning it; a simulator test that
  imports the backend constants would catch drift.
- The `faststream` pin above.

## Suggested PR order

1. ~~`fix/control-loop-safety`~~ done.
2. ~~`fix/tenancy-bind-self`~~ done.
3. `fix/web-contract-bugs`: trailing slashes, page reset, `toApiError` in fetchers, users edit
   dialog, field errors onto the form; decide Fix first #1.
4. ~~`chore/ci-hardening`~~ done.
5. ~~`perf/set-queries`~~ done.
6. ~~`chore/migration-safety`~~ done.
7. ~~`refactor/use-case-wiring`~~ done.

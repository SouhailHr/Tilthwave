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

Ordered by cross-tenant / data-loss risk. Each is small. The two control-loop items that
headed this list (the flow runner's swallowed `sys.exit`, the streamer skipping messages during a
DB outage) were fixed in `fix/control-loop-safety`.

1. **[A] Cross-tenant farm creation** (Medium, CWE-284). `repositories/base.py:104-128`
   `_bind_tenant` handles `column` and `via_zone`; `repositories/farm.py:15` declares
   `("self", "farm_name")`; `constants.py` gives `owner` write on farms. An owner of farm A can
   `POST /farms {"farm_name": "B"}` and create a row that nobody can see or delete through the API
   (blocks onboarding that name until someone touches the DB). Fix: treat `self` like `column` in
   `_bind_tenant`. Latent twin: no `via_sensor` branch either; unreachable today because
   `sensor-records` is read-only for every role, so add the branch before granting write.
2. **[A] `Idempotency-Key` is advertised and never honoured.** The web sends one per create
   (`_entity.ts:31-32`); the backend's only reference is the CORS allow-list (`main.py:51`).
   `irrigation_task` and `sensor_records` have no unique key, so a retried POST creates two tasks
   the flow runner acts on; on keyed resources the retry is a 409 shown as an error although the
   first attempt succeeded. Decide: implement (a dependency on the create routes keyed
   `(user_id, key)` that replays the stored response for ~24 h) or remove the header, the CORS
   entry and the comment at `_entity.ts:25`.

## Web (`apps/web`)

Bugs

- **[A] Search never resets pagination.** `entity-table.tsx:76` says "Reset to page 1 when the
  debounced search value changes"; nothing calls `setPage(1)`. Searching from page 3 shows an empty
  page. Fix: `useEffect(() => setPage(1), [debouncedSearch])`.
- **[A] List/detail queries surface raw Axios errors.** `_entity.ts:68,79` type the error as
  `ApiError` but the fetchers never call `toApiError`, so the dashboard, table and settings error
  states print "Request failed with status code 500". Fix: `.catch((e) => { throw toApiError(e) })`
  in the fetchers.
- **[A] Trailing-slash 307 on every by-id call and on login.** `_entity.ts:18,40,44` call
  `/{resource}/{id}/` and `auth.ts:39` `/auth/login/`; the backend routes are `/{id}` and `/login`
  with `redirect_slashes` at its default. The whole middleware chain (including the tenant user
  lookup) runs twice per call, and behind a proxy whose address is not in `FORWARDED_ALLOW_IPS` the
  redirect `Location` is `http://`, so the `Secure` cookie is dropped and the second hop is a 401.
  Fix: drop the slashes, then `FastAPI(redirect_slashes=False)` so any future mismatch is a loud
  404.
- **[A] Users edit dialog offers a Farm select the API discards.** `schemas/users.py:61` has
  `farm_name ... exclude=True`; `users/page.tsx` puts it in `editFields` and sends it: 200, success
  toast, farm unchanged. `UpdateUserInput` also still permits `is_superuser` and `password`, which
  `extra="forbid"` rejects with 422. Fix: drop `farm_name` from the edit fields (or add an
  admin-only `farm_name` to `UserUpdate`); narrow `UpdateUserInput` to what `UserUpdate` accepts.
- **[A] 422 field errors are parsed and never shown.** `errors.ts:51` builds `fieldErrors`;
  `EntityForm` never calls `form.setError` with them, so a 422 shows "Field required" with no field.

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
  (the other seven `api/*.ts` were trimmed), `errors.ts` `toastDescription`, `useDisclosure`
  `toggle`/`setOpen`; `_entity.ts` is imported by components despite the private-looking name.
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
- **Headers and env.** No `Strict-Transport-Security` (belongs on the production proxy).
  `NEXT_PUBLIC_API_BASE_URL` is not validated at build time.
- **[A] Tests: no form or page is tested.** `entity-form.tsx`, `entity-table.tsx`,
  `entity-crud-page.tsx`, the login/forgot/reset/settings pages, the `useCreateEntity` /
  `useUpdateEntity` invalidation, and the `isRedirecting` guard in `client.ts` (two simultaneous
  401s must emit `auth:expired` once). `_entity.test.ts` reaches into
  `api.interceptors.response.handlers[0]`; drive it through `api.get()` with a mocked adapter.
  First test to write: `entity-form.test.tsx` (empty submit → field errors, valid submit → parsed
  values, 422 → errors mapped onto fields).

## Backend (`apps/backend`)

Correctness and contract

- **[A] Sensor list and detail have different shapes.** `sensor_base.py:212-218` adds
  `assigned_to` in `_enrich_item` (list path only); `GET /sensors/{id}` returns the bare row. Fix:
  enrich in `get_by_id` too.
- **[A] Stats routes: two path shapes and 200-with-zeros for unknown names.** `/sensors/stats/`
  vs `/farms/stats/{farm_name}`; `farm.get_stats` and `zone.get_zone_data` never check the name
  exists, so a typo looks like an empty farm. Check existence first, 404 otherwise.
- **[A] Error envelope has no machine-readable code.** `helpers/errors.py` emits `{"detail": str}`
  only; use-case 422s carry a string while validation 422s carry a list, so the web branches on
  type. The web parses `error_code`, `request_id`, `message`, `errors`, none of which is sent. Fix:
  `CLIENT_FACING` values `(status, code)`, emit `{"detail", "code"}`; login stays 400 (the
  simulator retries on it as "admin not seeded yet"), so document that.
- **[A] Success bodies reuse `detail`** (`auth.py:114`, `account.py:60,65`) and login has two
  response shapes keyed on `use_cookie`. Use `{"message"}` for success and one `LoginResponse`.
- **[A] Timestamps are `str(datetime)` of a naive UTC column** ("2026-09-15 16:06:56.266864"),
  not ISO 8601. The web compensates in `utils/dates.ts`; any new client using `Date.parse` reads
  them as local time. Fix: `d.replace(tzinfo=UTC).isoformat()` in the adapter.
- **[A] Streamer handler is `async def` calling sync SQLAlchemy** (`run_streamer.py:41-46`), so
  every insert blocks the event loop and a DB stall stalls Kafka polling. Make it `def` (FastStream
  runs sync handlers in a thread); set `expire_on_commit=False` to drop the `refresh` round trip.
- **[A] Simulator retries a wrong password forever, silently.** `api_client.py:29-47` treats 400
  as "admin not seeded yet" and the backend returns 400 for bad credentials. Log the body on 400.

Performance (all O(N) where O(1) is easy; the Repository only exposes per-entity
`filter` / `first` / `count`, so every facade above it composes N small queries)

- **[A] Flow-runner tick ≈ 400 queries at 50 zones**: per zone the in-progress task, the zone
  sensors, one sensor lookup per zone-sensor for its type and one `first()` per sensor for the
  latest record; then `produce()` + `flush(5)` synchronously per command, so a slow broker makes
  the heartbeat stale. Fix: reuse the one in-progress-tasks query already made at `:181`,
  `zone_sensors JOIN sensor` for all zones, `SELECT DISTINCT ON (sensor_serial_number) ... ORDER BY
  sensor_serial_number, created_date DESC` (uses the existing index); one flush per zone.
- **[A] `/dashboard/summary` ≈ 125 queries** and loads every `sensor_record` of every water
  source into Python for the yearly sum; polled every 30 s per open tab. Fix: `GROUP BY status`
  (3 queries instead of 16 counts), `COUNT(*) WHERE zone_name IN (subquery)` for switchers and
  trees, `SUM((data->>'consumption')::numeric) GROUP BY date_trunc('month', created_date)`.
- **[A] Sensor list `_enrich_item` is a per-row query**: 21 queries for a page of 20, 101 for the
  FK picker. Fix: an `_enrich_items(entities)` hook with three `IN` queries.
- **[A] `/zones/stats/{zone}` loads all records of all zone sensors to keep 15** (`zone.py:336`),
  and runs the in-progress/completed task queries twice each (`:376-389`). No web caller.
- **[A] Missing index `irrigation_task(zone_name, status)`**; the flow runner filters on it per
  zone per tick and the dashboard counts by status.
- **[A] Engine pool is default** (5 + 10, no `pool_recycle`) while the API threadpool allows 40
  concurrent handlers. Set `pool_size`, `max_overflow`, `pool_recycle=1800`.

Data and migrations

- **Sensor records grow without bound.** No retention, rollup or cleanup; ~24k rows/week from the
  simulator at 15 s rounds. `sensor_records.data` is `JSON`, not `JSONB`. **[A]** Nothing queries
  `data` in SQL today, so JSONB brings no win yet, but converting later is a full rewrite under
  `ACCESS EXCLUSIVE`; decide now (convert while cheap, or record the decision to stay). No
  partition key either, and partitioning later means recreating the table. **[A]** Three wire
  timestamp formats reach `data.timestamp` (`%H:%M:%S` from the sensor simulator, `%H:%M` from the
  actuator simulator and the backend); settle that before any JSONB migration.
- **[A] Migration lock safety.** `alembic/env.py` runs all pending revisions in one transaction
  with no `lock_timeout`; `a1c2e3f4b5d6` built the `sensor_records` index without `CONCURRENTLY`.
  Safe on a fresh stack (`migrate` runs before every consumer), not for `make migrate` on a running
  one. Fix: `transaction_per_migration=True`, `SET lock_timeout`, an advisory lock, and
  `postgresql_concurrently=True` inside `autocommit_block()` for any future index on the growth
  table.
- **[A] `created_date` is nullable with an ORM-only default** (`tables/base.py:16`). Every
  "latest reading" is `ORDER BY created_date DESC LIMIT 1` and Postgres sorts NULL first under
  `DESC`, so any row inserted outside the ORM becomes the flow runner's current reading. Fix:
  `server_default=now()`, backfill, `SET NOT NULL`, mirrored in the model so `alembic check` stays
  green.
- **[A] `b2d3e4f5a6c7` downgrade destroys tenancy it cannot re-derive**: it drops
  `sensor.farm_name`, and a re-upgrade only backfills sensors that have a link row. Snapshot before
  dropping. Related: CI inserts its fixtures after `upgrade head`, so the backfill always runs on
  an empty table and a wrong JOIN would pass.
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

- **[A] No request / correlation id anywhere.** `errors.py` logs method + path only; api,
  streamer and flow runner share nothing but the wall clock; the web already reads `request_id`.
  Fix: a small ASGI middleware setting `X-Request-ID` into a ContextVar + `logging.Filter`, included
  in the 500 body.
- **[A] Observability is level 1**: plain-text logs via `basicConfig`, no metrics, and
  healthchecks cannot trigger restarts (`restart: unless-stopped` fires on exit only; the streamer
  now has one, `/health`, but a failing check still only shows in `docker ps`). Either monitor
  health externally or run an autoheal sidecar.
- **[A] `UVICORN_WORKERS` falls back to `2` in `docker/api/entrypoint.sh:18`** but `1` in compose;
  a non-compose run doubles the login rate limit.
- **[A] `mail.py:45-47` logs and continues after the 202**; the user never learns the reset mail
  failed. Acceptable, but it is the one true log-and-continue in the backend.

Security (Lows; policy decisions, none exploitable for data today)

- **[A] Rate-limit key trusts the first `X-Forwarded-For` hop** (`rate_limit.py:70-73`) when
  `API_TRUSTED_PROXIES` names the proxy but `FORWARDED_ALLOW_IPS` does not; an attacker then gets a
  fresh bucket per request. Take the rightmost hop not in `TRUSTED_PROXIES`, or rely on uvicorn's
  proxy headers alone.
- **[A] `worker` and `engineer` have `users:read`**: all staff PII, including through the
  simulator's worker credential. Drop it (the web's own profile comes from `/account`) or return a
  reduced projection for non-superusers.
- **[A] Live reset link written to the log when `SMTP_HOST` is unset.** Fine locally; a
  production stack that forgets SMTP logs every reset token. Gate on an explicit flag, or refuse
  startup when `API_COOKIE_SECURE=true` and SMTP is unset.
- **[A] `users.password` is filterable** through the Filter DSL (exact match only, bcrypt, not
  practically exploitable). Exclude `PRIVATE_FIELDS` in `_column`.
- **[A] No server-side revocation**: a captured JWT stays valid up to 120 min after logout; only a
  password change or deactivation kills it. Accepted for the stateless design.

Structure (from the design-patterns inventory; sized by the tech-debt audit)

- **[A] ~450 LOC of API surface nothing first-party consumes**: `/stats/`, `/select-list/`,
  `/identifier/`, `/auth/token/verify/`, all of `TreeUseCase`, the `get_stats` /
  `check_if_*_assigned` / `get_all_*` trios, half of `ZoneUseCase`; kept alive by two integration
  tests. Every one does an unbounded `filter()` in memory. Decide whether they are a contract for
  anyone; deleting them removes the unbounded reads and the `get_get_sensor_records` typo.
- **[A] Twenty inline use-case constructions outside `wiring.py`** (`zone.py:56-67,207,320`,
  `sensor.py`, `water_source.py`, `water_switcher.py`, `zone_sensors.py`, `farm.py:30-40`, where
  `FarmUseCase` builds a `ZoneUseCase` with six `None` repos). Causes the five
  `# to resolve the circular import` lazy imports and blocks substituting collaborators in tests.
  Inject the three real cross-aggregate collaborators from `wiring.py`; most other sites only need
  `self.<repo>.first(...)`.
- **[A] Duplicated sensor-type guard ×6** (`water_source.py`, `water_switcher.py`,
  `zone_sensors.py` create + update) and `update_by_serial_number` cloned between water source and
  switcher. One `require_sensor_of_type(serial, allowed)`.
- **[A] Tenancy is half a Strategy**: `_apply_tenant` knows four scope kinds, `_bind_tenant` two
  (the root cause of "Fix first" #1). Make `TENANT_SCOPE` an object with both `apply(query)` and
  `bind(data)` so a kind cannot be added to one side only; extracting it from the 439-line
  `BaseDBRepo` also makes it unit-testable.
- **[A] `get_irrigation_tasks` returns `None` instead of `[]`**, forcing `or []` in the flow runner
  and a double query in `zone.get_stats`.
- **[A] Entities are passed as dicts into the control loop** (`flow_runner.py:173`, then eleven
  `zone.get(...)`); the typed `Zone` dataclass is discarded at the boundary.
- **[A] `RESOURCES_FOR_ROLES` is written out four times** (admin = owner, worker = engineer
  verbatim); status enums are encoded twice (regex and list) and again in `dashboard.py`.
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
- **[A] Routes with no HTTP test**: `/farms` (the only `self` scope; list scoping unverified),
  `/water-sources`, `/water-switchers` GET/PATCH/DELETE, `/irrigation-tasks`, `/zone-sensors`.
- **[A] CSRF gate breadth**: only POST `/zones` and `/auth/logout` are tested; PATCH/DELETE via
  cookie, `/auth/password/*` via cookie, and "bearer + cookie → bearer wins" are not.
- **[A] Fixture tokens are minted without `pfp`** (`conftest.py:157-159`), so the suite runs on a
  token shape production never issues and `tenant.py:91` keeps a leniency branch for it. Mint via
  `AuthHelper.session_claims(user)`, then consider dropping the leniency. Password *reset*
  invalidating live sessions is untested (only change-password is).
- **[A] Postgres never runs the tests**; SQLite does not enforce FKs by default, so every
  FK-violation → 409 path behaves differently in production. The migrations job already has a
  Postgres service.

## Deploy / CI (`deploy`, `.github`)

- **[A] `uvx pip-audit` has no interpreter pin** (`ci.yml:30,95`): locally it picked Python 3.14
  and failed building `psycopg2-binary`; the same happens when the runner image's default moves.
  The export is pinned and hashed, so `--disable-pip` works and is faster. Drop the dead
  `--ignore-vuln PYSEC-2025-183` (affects PyJWT ≤ 2.10.1; 2.14 is installed).
- **[A] The simulator job never runs `uv run pytest`** (lint + audit only); its 9 tests are dead in
  CI. No coverage collection anywhere.
- **Production profile.** `deploy/README.md` describes a TLS reverse proxy, but the repo holds no
  proxy config and no "prod" env profile that flips `API_COOKIE_SECURE=true`,
  `API_DOCS_ENABLED=false`, a real `SMTP_HOST`, `API_WEB_BASE_URL`, `API_COOKIE_DOMAIN` and
  `BIND_ADDR` together. **[A]** No backup schedule either (`make db-dump` is manual);
  `.env.example` `DOMAIN=` is unused; `SMTP_TIMEOUT_SECONDS` exists in settings but compose does
  not forward it.
- **GitHub Actions pinned by tag, not SHA** (5 sites); base images by tag without digest
  (`python:3.12-slim`, `node:22-alpine`, `postgres:16-alpine`, Redpanda, console). Dependabot
  covers both ecosystems, so digests would stay maintained. **[A]** `apps/web/Dockerfile.dev` runs
  Node 25 while prod, CI and `engines` are Node 22, and runs `npm install` (not `ci`) at start.
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
2. `fix/tenancy-bind-self`: Fix first #1, `PRIVATE_FIELDS` out of the Filter DSL, `/farms` scope
   test, CSRF breadth test.
3. `fix/web-contract-bugs`: trailing slashes, page reset, `toApiError` in fetchers, users edit
   dialog, field errors onto the form; decide Fix first #2.
4. `chore/ci-hardening`: pip-audit pin, simulator tests in CI, action SHAs, Node 22 in
   `Dockerfile.dev`, fixture tokens via `session_claims`.
5. `perf/set-queries`: the `irrigation_task` index and the three N+1 shapes behind new
   set-oriented repository methods; sync streamer handler.
6. `chore/migration-safety`: per-migration transactions and lock timeout, `created_date`
   NOT NULL, the `b2d3` snapshot, CI backfill fixture.
7. `refactor/use-case-wiring`: delete the unconsumed surface, inject collaborators, the sensor-type
   guard, `TENANT_SCOPE` as an object. Largest; last.

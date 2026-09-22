# Backlog

What is known to be left, per area, as of 2026-09-22. Every item here was checked against the
code on `main` on that date; nothing is carried over from older audits without re-verification.
The three frontend documents this replaces (`HANDOFF.md`, `AUDIT.md`, `AUDIT_REAUDIT.md`, May
2026) are in git history; everything they listed as open has since been done except the items
under **Web** below.

Done and merged, so not listed: CI migration drift, the security round (CSRF gate before the
`/auth` exemption, cookie session, password fingerprint, login rate limit), httpOnly cookie auth
with a server-backed session, `/dashboard/summary/`, account settings and the forgot/reset
password flow, newest-first lists, full timestamps, sensor assignment, the user-menu crash.

## Web (`apps/web`)

- **Farm map.** The farm page was meant to carry a Leaflet map of the zones (`react-leaflet`).
  It is not installed and the page has no map. The only unfinished item of the original plan.
- **Stringly-typed numeric form fields.** Fifteen fields hold numbers as strings with a `refine`,
  and `positiveNumber` is duplicated in the trees and water-sources pages. The intended fix is a
  typed field config for `EntityForm` / `EntityCrudPage`, which is also what would make
  form-and-table integration tests cheap to write.
- **FK picker.** Loads the referenced resource with `size: 100`, no `staleTime`, and no
  "showing first N of M" when a resource has more than 100 rows.
- **Response validation.** Login, session and profile responses are Zod-parsed; entity lists are
  typed by hand and trusted. The decision behind it (OpenAPI codegen vs hand-written types) is
  open.
- **Telemetry.** `ObservabilitySink` logs and toasts; there is no vendor (Sentry, PostHog) and
  no `window.onerror` / `unhandledrejection` handler. Pick a vendor first.
- **Reliability knobs.** No mutation retry policy or backoff, no optimistic updates, no offline
  detection.
- **Dashboard shell.** `app/(app)/page.tsx` is a ~230-line client component; the RSC shell plus
  client islands refactor is open.
- **Headers and env.** No `Strict-Transport-Security` header (belongs on the production proxy,
  or `next.config.ts` headers). `NEXT_PUBLIC_API_BASE_URL` is not validated at build time; unset,
  the client falls back to the current origin.

## Backend (`apps/backend`)

- **Sensor records grow without bound.** There is no retention, rollup or cleanup; the local
  stack holds ~24k rows after a week of the simulator at 15 s rounds. `sensor_records.data` is
  `JSON`, not `JSONB`, so it cannot be indexed or queried efficiently. A retention job plus a JSONB
  migration is the largest open data item.
- **`ZoneUseCase`** is ~400 lines, twice the next largest use case: zone CRUD, sensor linking,
  latest-data assembly and trigger evaluation in one class.
- **Flow runner.** Still configured through the `configure()` Monostate, and each tick queries
  latest zone data and open tasks per zone in a loop (fine at 2 zones, N+1 at 50).
- **Concurrent edits.** PATCH has no `ETag` / `If-Match`; two admins editing the same row is
  last-write-wins.
- **Natural keys.** Zones, farms and sensors are referenced by name / serial rather than surrogate
  ids, so a rename cascades through the links. A design decision, not a bug.
- **`faststream` pinned at 0.5.48** (backend and simulator). 0.7 removed the `auto_commit`
  subscriber kwarg; upgrading needs a change in both subscribers and a live check against the
  broker, since the unit tests do not touch one.

## Deploy / CI (`deploy`, `.github`)

- **Production profile.** `deploy/README.md` describes a TLS reverse proxy, but the repo holds no
  proxy config, and there is no "prod" env profile that flips `API_COOKIE_SECURE=true`,
  `API_DOCS_ENABLED=false`, a real `SMTP_HOST`, `API_WEB_BASE_URL`, `API_COOKIE_DOMAIN` and
  `BIND_ADDR` together.
- **GitHub Actions are pinned by tag**, not commit SHA.
- **ESLint 10 and TypeScript 7** are blocked upstream (`eslint-config-next` still uses a removed
  ESLint API; `typescript-eslint` refuses TS 7). Re-check when Dependabot reopens them.
- **Kafka broker TLS / auth.** Deliberately not planned for now (the broker is not published
  outside the compose network). Listed so it is not forgotten.

## Simulator (`apps/simulator`)

Nothing beyond the `faststream` pin above.

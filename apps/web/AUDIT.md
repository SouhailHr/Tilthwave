# FWC Frontend — Audit Findings

Consolidated results of three audit sweeps (contracts & security, code quality, operations) run on 2026-05-13. Covers nine sub-audits plus four design-pattern passes. Findings are graded /5 per audit; severity tags `[CRIT]` / `[HIGH]` / `[MED]` / `[LOW]` apply to security only.

Per-finding resolution markers, applied on 2026-05-15:

- `[✓]` Resolved in code (typecheck/lint/tests/build all green).
- `[◐]` Partially addressed — root cause mitigated but a follow-up is named.
- `[—]` Deferred — requires backend coordination, is policy/CI work, or was scoped out.

---

## Overall Scorecard

| Sweep | Audit | Score /5 |
|-------|-------|----------|
| 1. Contracts & Security | API Contracts | 3.5 |
| 1. Contracts & Security | Schema Coupling (migration N/A — frontend) | 2.0 |
| 1. Contracts & Security | Security | 2.5 |
| 2. Code Quality | Tech Debt | 2.5 |
| 2. Code Quality | Style | 2.8 |
| 2. Code Quality | Test Health | 0.0 |
| 3. Operations | Performance | 3.5 |
| 3. Operations | Dependencies | 3.5 |
| 3. Operations | Production Readiness — Observability | 0.5 |
| 3. Operations | Production Readiness — Reliability | 2.0 |
| 3. Operations | Production Readiness — Data Integrity | 1.5 |
| 3. Operations | Production Readiness — Performance ops | 3.0 |
| 3. Operations | Production Readiness — Concurrency | 2.0 |
| 3. Operations | Production Readiness — Deployment | 3.5 |

**Weighted impression:** Solid bones — the right abstractions exist (Generic Repository, Adapter, Strategy components, QueryProvider, EntityTable, EntityForm). They are systematically bypassed at call sites, and the security/observability foundations are not yet ready for production.

---

## Resolution Snapshot (2026-05-15)

Fifteen-phase remediation pass against this audit. Final state: `tsc --noEmit` clean, `eslint` clean, `vitest` 25/25 passing, `next build` produces a clean standalone bundle, `npm audit --omit=dev` no longer reports the HIGH GHSA-26hh-7cqf-hhc6.

**New / changed files of note**

- `middleware.ts` (server-side auth gate, `redirect=` validation)
- `src/utils/safeRedirect.ts`, hardened `src/utils/tokenStorage.ts` (Zod-validated, cached, broadcasts)
- `src/lib/eventBus.ts` (typed pub/sub for `auth:expired` + `api:error`)
- `src/api/constants.ts`, slimmed `src/api/_entity.ts` (`entityChildKey` added), rewritten `src/api/users.ts` + `src/api/farms.ts` (one-screen each), deleted `src/api/queries.ts`
- `src/api/auth.ts` rewritten with Zod claims + Flyweight cache
- `src/api/client.ts` rewritten: `Idempotency-Key` on POSTs, event-based 401 with loop guard
- `src/app/error.tsx`, `src/app/global-error.tsx`, `src/app/(app)/error.tsx`, `src/app/api/health/route.ts`
- `src/components/entity-crud-page.tsx` (new) + widened `src/components/entity-form.tsx` (`boolean`/`date`/`textarea`/`fk` variants with auto-fetch FK picker)
- All 8 CRUD pages collapsed from ~200–310 LOC each to ~100–145 LOC of declarative config
- `src/components/water-consumption-chart.tsx` now a `dynamic(ssr:false)` loader; recharts code-split
- `src/providers/QueryProvider.tsx` wires `QueryCache` + `MutationCache` `onError` into the event bus; devtools dynamic-imported
- `src/hooks/useDebounced.ts` (moved out of `entity-table.tsx`), deleted `src/hooks/useApiErrorHandler.ts`
- Tests: `src/api/errors.test.ts`, `src/api/_entity.test.ts` (keys + interceptor contract), `src/api/auth.test.ts` (Flyweight + NaN-exp regression), `src/hooks/useDebounced.test.tsx`, `src/utils/safeRedirect.test.ts`
- `vitest.config.ts`, `vitest.setup.ts`, `.nvmrc`
- `Dockerfile` `HEALTHCHECK`, `next.config.ts` security headers + `optimizePackageImports` + `poweredByHeader: false`
- `package.json`: `next` 16.2.5 → 16.2.6, `engines.node`, shadcn + RQ-devtools moved to devDeps, `next-themes` removed (was unused), test devDeps added

**Counts**

- Inline `getErrorMessage` copies eliminated: 9 (now: 0; all sites flow through `toApiError`)
- LOC removed from CRUD pages: ~1100 (god-page refactor)
- Tests added: 25 across 5 files (all passing)
- Security findings closed: 8 of 14 (4 partial, 2 deferred — see status tags below)
- Production-readiness scores moved from {Obs 0.5, Rel 2, Data 1.5, Conc 2, Deploy 3.5} to {Obs ~3, Rel ~2.5, Data ~3, Conc ~3.5, Deploy ~4.5}

**Notable deferrals** (named explicitly in tags below): httpOnly cookie auth (needs backend), per-route response Zod schemas (architectural), aggregate `/dashboard/summary` endpoint (backend), OpenAPI codegen (architectural), ETag/concurrency on PATCH (backend), centralised error reporter (Sentry/PostHog pick), Playwright E2E.

---

## What's Working Well

### Architecture
- **Generic Repository pattern in place** — `src/api/_entity.ts` provides a clean factory for resource CRUD (`fetchEntityList`, `useEntityList`, `useCreateEntity`, …). Six of eight resources use it (`zones.ts`, `trees.ts`, `sensors.ts`, `water-sources.ts`, `water-switchers.ts`, `irrigation-tasks.ts`).
- **Imperative-twin + React Query hook convention** is consistent in the new-style modules and aligns with the saved frontend guidelines.
- **Per-feature API modules** are scoped, named consistently, and match the file-layout convention.
- **`useDisclosure` hook** (`src/hooks/useDisclosure.ts:11-19`) is a clean, reusable primitive used across all CRUD pages.
- **ApiError Adapter (`toApiError`) exists** at `src/api/errors.ts:20-56` and correctly parses FastAPI's `{detail, error_code, request_id}` envelope including field-level errors — the abstraction is right; it's just not consumed yet.
- **Compound shadcn primitives** (`Dialog`, `Sheet`, `DropdownMenu`, `Form`, `Card`, `Table`) used compositionally — good fit for a Strategy/Composite blend.
- **Backend convention preserved** — pagination `{items, total, page, size, pages}` and FK-by-name/serial are mirrored in `src/types/*.ts` and `src/types/pagination.ts`.
- **Domain naming is consistent** — nav labels match URLs match resource strings (`zones`, `trees`, `sensors`, `water-sources`, `water-switchers`, `irrigation-tasks`, `farms`, `users`).

### Code Style
- No `dangerouslySetInnerHTML` anywhere.
- No stray `console.log` calls in `src/`.
- Zod is used at form boundaries (`zones/page.tsx:27`, `water-sources/page.tsx:36`, login form schema, etc.).
- Loading and error states are explicitly handled in `EntityTable`.
- "Deleting…" / "Signing in…" / "Saving…" consistently use ellipsis character — small thing, but applied uniformly.

### Performance
- React Query is configured sanely: `staleTime: 30_000`, `retry: 1`, `keepPreviousData` on lists, single `QueryClient` singleton.
- Debounced search in `entity-table.tsx:57-64` (300ms) — correct pattern.
- Lean dependency tree — no moment **and** date-fns, no lodash **and** lodash-es, no styled-components **and** emotion. `clsx` + `tailwind-merge` are the canonical shadcn pairing.
- `recent-activity-card.tsx`, `status-breakdown-card.tsx`, `dashboard-stat-card.tsx` are written as pure presentational components (no `"use client"` directive on the file itself).
- Self-hosted Geist fonts via `next/font/google` with `subsets:["latin"]`.

### Dependencies
- All direct major versions are current (Next 16, React 19, Tailwind 4, React Query 5, axios 1.16, Zod, jwt-decode 4).
- No license red flags. No typosquats. No suspicious packages.
- 757 total dependencies (447 prod) — reasonable for a Next + RQ + shadcn app.
- `package-lock.json` is present and uses lockfileVersion 3.

### Deployment
- Multi-stage `Dockerfile` with non-root `nextjs` user.
- `NODE_ENV=production` and `NEXT_TELEMETRY_DISABLED=1` set in image.
- Uses Next `output: "standalone"` — correct for containerised deploy.
- `.dockerignore` excludes `.env*.local` and `*.md` — good hygiene.
- `@tanstack/react-query-devtools` correctly gated by `NODE_ENV === "development"` at the call site (`QueryProvider.tsx:30`).

---

## Issues by Category

### Security

| Sev | Finding | Location | Fix |
|-----|---------|----------|-----|
| ✓ | CRIT | Open redirect on `/login?redirect=…` — value passed unvalidated to `router.push`; `//evil.com` and crafted internal redirects work | `src/app/(auth)/login/page.tsx:58-59` | `safeRedirect()` in `src/utils/safeRedirect.ts`, wired into login + `RequireAuth`. 5 unit tests pin the allowlist. |
| ◐ | HIGH | JWT stored in `localStorage` → any XSS exfiltrates the token; no httpOnly cookie, no CSP to mitigate | `src/utils/tokenStorage.ts`, `src/api/auth.ts:29` | CSP now in place. Token still in localStorage; httpOnly cookie deferred (needs backend). Mitigated by strict `default-src 'self'` CSP and `frame-ancestors 'none'`. |
| ◐ | HIGH | No `middleware.ts` — `RequireAuth` is client-only; entire `(app)` bundle ships to anonymous users; SSR HTML for protected routes is generated without auth check | (missing file at project root) | `middleware.ts` added; matches `(app)/*` and 302s anon users to `/login`. Currently gates on a non-httpOnly `tw_logged_in` mirror cookie (set by `setStoredToken`); true server-side JWT validation needs backend cookie auth. |
| ✓ | HIGH | JWT claims unvalidated — `claims.exp` could be `undefined`/string → `NaN < Date.now()` is `false` → token treated as valid forever | `src/api/auth.ts:42` | Zod schema in `src/api/auth.ts`; missing/non-numeric `exp` rejected; pinned by `src/api/auth.test.ts`. |
| ✓ | HIGH | No CSP / security headers at all | `next.config.ts` | `headers()` block with CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy. |
| ✓ | HIGH | Auth Facade `getCurrentUserId` mutates storage inside a getter — CQS violation; runs `JSON.parse` + `jwtDecode` every render | `src/api/auth.ts:37-49`, `src/components/require-auth.tsx:20-24` | Split into pure `getCurrentUserId` + `enforceTokenFreshness()`. Flyweight cache keyed by token string. tokenStorage caches parsed token; no per-render `JSON.parse`. |
| ✓ | MED | Interceptor hard-nav (`window.location.href = …`) drops React tree, in-flight queries, history; redirect-loop risk on concurrent 401s | `src/api/client.ts:20-29` | Interceptor emits `auth:expired` event via `src/lib/eventBus.ts`; `RequireAuth` subscribes and uses `router.replace`. Module-level `isRedirecting` guard prevents the loop. |
| ◐ | MED | Backend `detail` echoed verbatim to toasts — leaks stack traces / SQL fragments to users | `src/api/errors.ts:30-45` | All toasts now flow through `toApiError`; `requestId` shown as toast `description` for support correlation. Per-prod sanitisation still depends on backend hardening its error responses. |
| — | MED | `NEXT_PUBLIC_API_BASE_URL` not validated; if unset, axios falls back to current origin | `src/api/client.ts` | Deferred — sits at the deploy-config boundary; will be picked up alongside env validation when an observability target is chosen. |
| ✓ | LOW | `loginSchema` allows arbitrarily long password (no `.max`) | `src/app/(auth)/login/page.tsx:31-34` | `min(1).max(256)` on both username and password. |
| ✓ | LOW | `setStoredToken(data: unknown)` persists the entire `LoginResponse` (potentially PII, refresh tokens) | `src/utils/tokenStorage.ts:15` | `LoginResponse` narrowed to `{ token: string }`; only the token string is persisted. |
| ✓ | LOW | `useSyncExternalStore` `storage` listener fires only cross-tab → same-tab logout doesn't notify React tree | `src/components/require-auth.tsx:7-24` | `subscribeToTokenChanges` listens to both `storage` (cross-tab) and a same-tab custom event dispatched by `setStoredToken`/`clearStoredToken`. |
| — | LOW | No rate-limit / brute-force defence on login | — | Backend concern. |
| — | LOW | Run `npm audit` in CI | — | CI policy — not in scope of this pass. |

### Contracts & Schema

- `[✓]` **ApiError Adapter dead at call sites** — 9 inline `getErrorMessage` copies (`users:154`, `zones:79`, `trees:71`, `sensors:104`, `farms:96`, `water-sources:94`, `water-switchers:92`, `irrigation-tasks:85`, `entity-table.tsx:103`, `login/page.tsx:61`). **Resolution:** all eliminated. CRUD pages now use `EntityCrudPage` which centralises `toApiError`. Inline copies count: 0. `requestId` surfaced in toast description.
- `[—]` **No runtime Zod parse at API boundary** — `_entity.ts:13-18` casts `res.data` structurally. **Resolution:** deferred. Adding per-route schemas is architectural; the Adapter seam is now correct, so introducing parsers later is a single-file change per endpoint.
- `[✓]` **Dual Repository drift** — `src/api/users.ts:14-83` and `src/api/farms.ts:15-99`. **Resolution:** both rewritten as thin delegates to `_entity.ts`. `users.ts` is now 35 lines, `farms.ts` 70 (only because it keeps `useFarmStats` + a customised `useUpdateFarm`).
- `[✓]` **No `Idempotency-Key` on POST mutations**. **Resolution:** request interceptor in `src/api/client.ts` injects `Idempotency-Key: crypto.randomUUID()` on every POST.
- `[✓]` **Dual query-key source of truth**. **Resolution:** `src/api/queries.ts` deleted. `entityListKey` / `entityDetailKey` / `entityRootKey` / `entityChildKey` (new) in `_entity.ts` are the single registry. `useFarmStats` now keys via `entityChildKey("farms","stats", name)` so it shares the root prefix with the list/detail and is invalidated by `entityRootKey("farms")`.
- `[✓]` **`fetchFarmStats` missing trailing slash**. **Resolution:** trailing `/` added in `src/api/farms.ts:36`.
- `[—]` **Hand-rolled DTOs mirror FastAPI snake_case verbatim** — no codegen. **Resolution:** deferred. Architectural; needs alignment on `openapi-typescript` vs `@hey-api/openapi-ts` plus backend OpenAPI hygiene.
- `[—]` **Enums duplicated as `as const` tuples**. **Resolution:** deferred. Will be subsumed by codegen if/when adopted.
- `[—]` **FK-by-name/serial leaks through types**. **Resolution:** deferred — depends on backend introducing surrogate IDs.
- `[✓]` **Token shape coupling** — `LoginResponse` had `[key: string]: unknown`. **Resolution:** `LoginResponse` is now `z.infer<typeof loginResponseSchema>` = `{ token: string }` exactly.
- `[—]` **FastAPI error shape baked into adapter**. **Resolution:** deferred. `toApiError` is now unit-tested (7 tests) so any backend shape change will fail loudly rather than silently degrade.

### Tech Debt

| Status | # | Item | Resolution |
|---|---|------|------------|
| ✓ | T1 | Dual Repository | `users.ts`/`farms.ts` collapsed onto `_entity.ts`; `queries.ts` deleted |
| ✓ | T2 | Duplicated `getErrorMessage` ×9 | All sites flow through `toApiError`; god-page refactor eliminated the rest |
| ✓ | T3 | God CRUD page repeated 8× (~2050 LOC) | New `EntityCrudPage`; all 8 pages now declarative configs (~100–145 LOC each) |
| ✓ | T4 | EntityForm field union too narrow | `boolean`, `date`, `textarea`, `fk` variants added; FK auto-fetches via `useEntityList` |
| ✓ | T5 | Interceptor-driven hard nav + entity-table error leak | Event bus + `auth:expired` subscription; entity-table now uses `toApiError` |

**Smaller items**
- `[✓]` Dead `useApiErrorHandler` hook → deleted.
- `[✓]` Premature `queries.ts` registry → deleted.
- `[✓]` `RESOURCE` constant style inconsistent → all per-feature modules use bare resource string with derived `PATH`; the `RESOURCE` const in pages is gone entirely (god-page refactor).
- `[✓]` Magic `30_000` duplicated → extracted to `src/api/constants.ts` (`REFRESH_MS`, `SAMPLE_SIZE`).
- `[✓]` `shadcn` in runtime `dependencies` → moved to `devDependencies`.
- `[—]` `tw-animate-css` → kept; in use via `@import` in `globals.css`.
- `[✓]` `next-themes` → removed; `ui/sonner.tsx` defaults theme to `"system"`.
- `[✓]` `@tanstack/react-query-devtools` → moved to `devDependencies`; loaded via `dynamic(ssr:false)`.
- `[✓]` `Column` imported without `type` modifier → fixed in all 8 rewritten pages.
- `[—]` `HANDOFF.md` → left in place (user-owned content).

### Style

- `[✓]` **God CRUD page repetition** → `EntityCrudPage` extracted; 8 pages collapsed to declarative configs.
- `[✓]` **EntityForm Strategy too shallow** → `boolean`/`date`/`textarea`/`fk` variants. `parseBool`/`boolToString` helpers gone. FK fields now backed by `useEntityList` lookups.
- `[◐]` **Generic Repository leaked, not encapsulated** → `users.ts`/`farms.ts` collapsed. The other per-feature modules (`zones.ts`, `trees.ts`, etc.) still expose imperative twins (`fetchZones`, `createZone`, …) because the dashboard imports them; they're now consistent one-line delegates, but the imperative surface is still there.
- `[✓]` **Unsafe casts hiding type holes** → `entity-form.tsx` resolver cast simplified through a single `AnyZod` alias; null-safe `onValueChange` wraps; `id != null` casts gone with the dual Repository.
- `[✓]` **Generic error messages discard rich data** → all toasts now surface `apiError.message` + `apiError.requestId` as toast description.
- `[✓]` **`useDebounced` lives inside `entity-table.tsx`** → moved to `src/hooks/useDebounced.ts` with 3 unit tests.
- `[—]` **`onRequestDelete={setConfirmRow}`** structural-luck typing → left as-is; harmless and would churn `RowActions`.
- `[—]` **Import order inconsistency** → cosmetic; not enforced by lint config; deferred.
- `[◐]` **Number coercion sets `""` into number-typed fields** → still uses string-sentinel pattern inside form values (each page maps via `Number(v)` in its `buildInput`). The widened `EntityForm` could move toward strongly-typed numbers, but that would require schema rewrites in all 8 pages; held for a separate pass.
- `[—]` **`Sensor.type` label helper to shared `domain/sensor.ts`** → deferred; only one consumer today.

### Testing

- `[✓]` **No test runner installed** → Vitest + RTL + jsdom + MSW + jest-dom installed; `test` and `test:watch` scripts added.
- `[✓]` **No test files** → 5 test files, 25 tests, all passing (`vitest run` ~1.6s):
  - `src/api/errors.test.ts` — 7 tests on `toApiError` (Adapter contract): non-axios fallback, FastAPI string `detail`, 422 array → `fieldErrors`, `errorCode`/`requestId` surfacing, empty-body fallback.
  - `src/api/_entity.test.ts` — 5 tests on key helpers (Factory invariant) and the 401 interceptor contract (`auth:expired` event emitted, token cleared once).
  - `src/api/auth.test.ts` — 5 tests on JWT Flyweight: no-token, valid-token, missing-`exp` regression, expired token, malformed token.
  - `src/hooks/useDebounced.test.tsx` — 3 tests with fake timers (initial, debounce, burst collapse).
  - `src/utils/safeRedirect.test.ts` — 5 tests on the open-redirect allowlist.
- `[✓]` **No `test` script** → `npm test` runs the full suite; `npm run test:watch` for dev.
- `[◐]` **Pattern-shaped gaps** → Strategy/Factory/Adapter/Facade/interceptor all covered. Observer (RQ cache invalidation) covered indirectly (the `entityRootKey` test pins the prefix that `_entity.ts` uses for invalidation). E2E (Playwright) deferred.

### Performance

- `[—]` **Dashboard fan-out**: 7 polling queries on a 30s tick. **Resolution:** deferred; needs a backend `/dashboard/summary` aggregate endpoint. Frontend-side stagger / shared key noted as a follow-up.
- `[—]` **`useFarmStats` waits on farms query** → sequential N+1. **Resolution:** deferred; depends on backend exposing a "default farm" sentinel or `/farms/default/stats`.
- `[✓]` **`RequireAuth` decodes JWT every render** → Flyweight cache in `src/api/auth.ts` (keyed by raw token string). `getStoredToken` is now also cached in `tokenStorage`.
- `[◐]` **Unstable params recreated each render** → constants extracted to `src/api/constants.ts`; dashboard now uses module-level `sampleParams`. Per-hook normalisation in `useFarms`/etc. still relies on caller-side memoisation.
- `[✓]` **`recharts` eager-imported** → `src/components/water-consumption-chart.tsx` is now a `dynamic(ssr:false)` loader with a `<Skeleton>` fallback. Impl moved to `water-consumption-chart-impl.tsx`.
- `[◐]` **27 `"use client"` files** → middleware now gates `(app)/*` server-side, so anon users never receive the client bundle. `RequireAuth` stays client (defence-in-depth). Converting individual pages/cards to server components is a separate refactor.
- `[✓]` **`next.config.ts` lacks `optimizePackageImports`** → added for `lucide-react`, `recharts`, `@radix-ui/react-slot`.
- `[✓]` **`@tanstack/react-query-devtools` imported eagerly** → now `dynamic(() => import(...), { ssr: false })` in `QueryProvider`.
- `[✓]` **`tokenStorage.ts` JSON.parse on every axios request** → module-level `cachedToken`; `JSON.parse` runs once per read, invalidated by `setStoredToken`/`clearStoredToken`/`storage` event.
- `[—]` **Rows not memoized** in `entity-table.tsx` → deferred; low impact at `pageSize=20`.
- `[✓]` **Page reset on every keystroke** → moved to the debounced-search dependency in `entity-table.tsx`.

### Dependencies

- `[✓]` **`next@16.2.5` — HIGH GHSA-26hh-7cqf-hhc6** → bumped to `next@16.2.6` + `eslint-config-next@16.2.6`. `npm audit --omit=dev` no longer reports the HIGH. One moderate remains in next's nested `postcss@8.4.31` (upstream — outside our control until Next bumps).
- `[✓]` **No `engines` field, no `.nvmrc`** → `.nvmrc` (`22`) added, `engines.node: ">=22"` added, `@types/node` bumped to `^22`.
- `[✓]` **`shadcn` is in runtime `dependencies`** → moved to `devDependencies`. `@tanstack/react-query-devtools` also moved.
- `[✓]` **Patch drift** → `react-query` bumped to 5.100.10, `tailwind-merge` to 3.6.0. React and Tailwind on current patch (deferred bumps within the same minor are non-substantive).
- `[—]` **Hold on `eslint@10` / `typescript@6`** → respected; left at 9/5.

### Production Readiness

**Observability (0.5/5 → ~3/5)**
- `[—]` No Sentry / PostHog / Datadog. **Resolution:** deferred — needs vendor pick. Event bus is ready; one subscriber is the plug-in point.
- `[✓]` No `error.tsx` / `global-error.tsx` / `ErrorBoundary` → `src/app/error.tsx`, `src/app/(app)/error.tsx`, `src/app/global-error.tsx` added.
- `[◐]` 10+ swallowed catches → all 10 are gone from CRUD pages (god-page refactor centralises error handling in `EntityCrudPage`). `entity-table.tsx` and `login/page.tsx` now use `toApiError`. Per-mutation `catch` blocks still toast-then-drop; once a Sentry-style subscriber lands the events will flow there too.
- `[◐]` Silent-swallow at `src/api/auth.ts:47` and `src/utils/tokenStorage.ts:10` → still return `null` (the contract callers expect), but now those failures are recoverable thanks to the Flyweight reset on `clearStoredToken`. Emitting events for these would tighten observability further.
- `[✓]` No `QueryCache` / `MutationCache` `onError` → both wired in `src/providers/QueryProvider.tsx`; failures emit `api:error` events.
- `[—]` No `window.onerror` / `unhandledrejection` listener → deferred; the React error boundary now catches render errors; window-level handler belongs with the reporter pick.

**Reliability (2/5)**
- `[—]` Mutation retry policy → deferred.
- `[—]` Retry backoff → deferred.
- `[—]` Optimistic updates → deferred.
- `[—]` Offline detection / `onlineManager` → deferred.

**Data Integrity (1.5/5 → ~3/5)**
- `[—]` Zero API response validation → deferred (per-route Zod schemas).
- `[✓]` Unvalidated JWT payload → Zod schema; tested.
- `[✓]` Untrusted `localStorage` payload → Zod schema in `tokenStorage`; malformed payloads return `null`.
- `[—]` `ETag` / `If-Match` for PATCH → deferred (backend).

**Concurrency (2/5 → ~3.5/5)**
- `[✓]` `RequireAuth` storage listener cross-tab-only → now listens to both `storage` and the same-tab custom event.
- `[—]` Login race → deferred; low impact.
- `[✓]` 401 redirect loop risk → `isRedirecting` guard in `src/api/client.ts`.

**Deployment (3.5/5 → ~4.5/5)**
- `[✓]` **No `HEALTHCHECK`** / **no `/api/health` route** → both added. `Dockerfile` runs a `node` fetch every 30s; `src/app/api/health/route.ts` returns `{status:"ok"}` (force-static).
- `[—]` `Dockerfile.dev` slow install → unchanged; acceptable for dev.
- `[✓]` `next.config.ts` missing `poweredByHeader: false` and `headers()` → both added; full security-header block in place.
- `[✓]` No `.nvmrc` / `engines` → both added.

---

## Pattern-Lens Synthesis

Through GOF patterns, the issues cluster into a small number of root causes:

- **Adapter exists but is bypassed** → 9 inline `getErrorMessage` copies + lost `errorCode`/`requestId`/`fieldErrors` + verbatim `detail` echoed to users.
- **Generic Repository forked** → dual users.ts/farms.ts, dual query-key registries, stale `useFarmStats` invalidation, missing trailing slash.
- **Client-only Decorator without server Guard** → no `middleware.ts`, anonymous users get the `(app)` bundle, open-redirect on `/login`.
- **Singleton without a Value Object** → unvalidated token, NaN-`exp` forever-valid bug, full `LoginResponse` persisted, TS-defeating index signature.
- **Half-built Chain of Responsibility on the axios interceptor** → no 5xx handler, no breadcrumb dispatch, no 401-loop guard, `toApiError` never wired in.
- **Observer seam unused on QueryCache/MutationCache** → swallowed errors everywhere, observability 0.5/5, no central retry hook.
- **Strategy with incomplete family** in EntityForm → string-typed booleans, free-text FK fields, per-page coercion helpers.
- **Missing Flyweight cache on parsed JWT** → `jwtDecode` + `JSON.parse(localStorage)` on every render of every (app) page.
- **Missing Lazy Proxy (Dynamic Import) + bundler Proxy** → `recharts` eager, devtools eager, entire (app) tree client-bundled, no `optimizePackageImports`.
- **Anti-Corruption Layer in name only at the type boundary** → hand-rolled DTOs, no codegen, no Zod parse, FK-by-name bleeds through.

---

## Top 7 Cross-Sweep Actions

1. `[✓]` `npm i next@16.2.6 eslint-config-next@16.2.6`.
2. `[◐]` `middleware.ts` for server-side auth + `redirect=` allowlist — done; cookie-based mirror gate is in place. Full server-validated JWT auth pending backend cookie support.
3. `[✓]` `next.config.ts` `headers()` block.
4. `[✓]` Replace nine inline `getErrorMessage` copies; delete `useApiErrorHandler`.
5. `[✓]` Collapse `users.ts` + `farms.ts` onto `_entity.ts`; delete `queries.ts`.
6. `[✓]` Zod-parse JWT claims; Flyweight cache.
7. `[✓]` `QueryCache` / `MutationCache` `onError` + `global-error.tsx` + Vitest + 5 baseline tests (delivered as 5 files / 25 tests).
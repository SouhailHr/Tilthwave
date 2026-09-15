# FWC Frontend — Re-Audit (post-remediation)

Second pass of the three sweep skills (contracts & security, code quality, operations) run on 2026-05-15 against the post-remediation codebase. Companion to `AUDIT.md`, which carries the original audit plus inline resolution markers.

This document captures the **new findings surfaced by the second pass** — regressions introduced by the remediation, latent issues the first pass missed, and degenerate patterns where remediation wired up half of a structure (Observer with no sink, Chain of Responsibility with one link, etc.).

---

## Top-line Summary

Scores moved up across every dimension. Headline regressions to address next:

1. **Per-attempt Idempotency-Key** defeats its own dedupe semantics (every retry sends a fresh UUID).
2. **`useUpdateFarm` bypasses `useUpdateEntity`** — skips detail-cache invalidation; `useFarm(id)` shows stale data after edit.
3. **Typed event bus has zero sinks for `api:error`** — `QueryProvider.onError` emits into the void.
4. **Imperative-twin duplication** in 6 per-feature modules (~25 dead wrappers; one already drifted: `useUpdateFarm`).
5. **`tw_logged_in` cookie is spoofable** — middleware is a UX hint, not a security control.
6. **Middleware has no `try/catch`** — any Edge-runtime throw 500s the entire site.
7. **`/api/health` is `force-static`** — essentially TCP liveness, not readiness.

Pattern-level diagnosis: most remaining gaps are **degenerate patterns** (one-link chains, one-strategy strategies, Observers with no sink) — finish what was started before adding new abstractions.

---

## Pattern Vocabulary (post-remediation)

**Actively in use**

| Pattern | Where |
|---|---|
| Front Controller / Guard | `middleware.ts` + `src/components/require-auth.tsx` |
| Typed Observer / Pub-Sub | `src/lib/eventBus.ts` (`AppEvent: auth:expired \| api:error`) |
| Adapter | `toApiError` in `src/api/errors.ts` — now uniformly wired |
| Template Method + Strategy | `src/components/entity-crud-page.tsx` |
| Composite + Strategy | `src/components/entity-form.tsx` (tag-union `FieldRenderer`) |
| Flyweight | `claimsCache` in `src/api/auth.ts`, `cachedToken` in `src/utils/tokenStorage.ts` |
| Lazy Proxy | `next/dynamic` for recharts (`water-consumption-chart.tsx`) + devtools (`QueryProvider.tsx`) |
| Facade | `src/api/_entity.ts` + per-feature thin delegates |
| Registry | `entityListKey` / `entityDetailKey` / `entityRootKey` / `entityChildKey` |
| Chain of Responsibility | `src/api/client.ts` — **single-link only** |
| Module Singletons | `api` axios instance, `isRedirecting`, `claimsCache`, `cachedToken`, `eventBus` listeners |

**Anti-patterns / degenerate patterns surfaced**

- **Imperative-Twin Duplication** — 6 per-feature modules expose `fetchOne/create/update/delete` wrappers with **zero external callers**; `_entity` Repository already does the job. Adapter-without-adaptee.
- **Two Observers, one weak** — typed `eventBus` (in-process, type-safe) coexists with a spoofable cookie + `window` event channel for auth state.
- **Observer with no sink** — `QueryProvider` emits `api:error` events; the only subscriber is `RequireAuth` filtering for `auth:expired`. `api:error` is unconsumed.
- **Degenerate Chain of Responsibility** — `client.ts` interceptor mixes auth-header, Idempotency-Key, 401 detection, redirect-guard, event emit in one handler.
- **Broken Template Method** — `useUpdateFarm` (`src/api/farms.ts:46-60`) reimplements the algorithm instead of overriding a Strategy slot, skipping the detail-key invalidation step.
- **Null Object lying about identity** — `entityChildKey(RESOURCE, "stats", farmName ?? "")` produces a valid cache key when `farmName` is null.
- **Speculative Generality in `entityChildKey`** — typed key constructor accepts `string` segments, defeating its typing purpose.
- **`as never` epidemic** — 8 casts in `src/app/(app)/users/page.tsx` papering over generic-constraint gaps in `EntityCrudPage`.
- **Mediator missing for UI side effects** — reusable components (`EntityCrudPage`, `EntityTable`) call `toast.*` directly; `eventBus` is built but unused for UI feedback.

---

## Scorecards

### Sweep 1 — Contracts & Security

| Audit | Score /5 | Critical Gaps |
|-------|---------|---------------|
| API Contracts | 3.5 | Idempotency-Key per-attempt; imperative twins in 6 modules; no response-shape Zod; `useUpdateFarm` cache-stale; FK picker silent truncation past 100 |
| Migration / Schema Coupling | 2.5 | FK select string-indexes `Record<string, unknown>`; `entityChildKey` namespace untyped; `chart_data` month-name keys unvalidated; cookie/JWT TTL drift |
| Security | 4.0 | `tw_logged_in` UX-hint spoofable; same-origin XSS forges `tw-auth-change`; `safeRedirect` accepts encoded-slash payloads; Idempotency-Key on `/auth/login` |

### Sweep 2 — Code Quality

| Audit | Score /5 | Key Finding |
|-------|---------|-------------|
| Tech Debt | 3.8 | Imperative-Twin Duplication ×6; toast coupling in reusable components; `as never` × 8; module Singletons hard to test; per-request Idempotency-Key |
| Style | 3.5 | `EntityCrudPage` 14 props + 5 generics (Ousterhout-shallow); `AnyZod` cast; `create`/`edit`/`update` naming drift; `buildInput` repeated 8×; `toastDescription`/`getErrorMessage` exported but unused |
| Test Health | 2.5 | 25 unit / 0 integration / 0 E2E; MSW + user-event installed-but-unused; `_entity.test.ts` reaches into private axios state; remediation-introduced bugs untested |

### Sweep 3 — Operations & Infrastructure

| Audit | Score /5 | Critical Gaps |
|-------|---------|---------------|
| Performance | 3.5 | Dashboard fan-out (7 polls + N+1) deferred; FK picker fires N queries per dialog; `(app)/page.tsx` still client-shelled despite middleware gate; `optimizePackageImports` missing `@base-ui/react` |
| Dependencies | 4.0 | 1 prod moderate (next's nested postcss — upstream); 6 dev-only moderates via vitest@2 → esbuild; MSW + user-event unused; `shadcn` mis-classified |
| Production Readiness | per-dim | see below |

**Production readiness per-dimension (Δ vs prior pass):**

| Dimension | Prior | Now | Δ |
|---|---|---|---|
| Observability | 0.5 | 2.0 | +1.5 |
| Reliability | 2.0 | 2.5 | +0.5 |
| Data integrity | 1.5 | 2.5 | +1.0 |
| Concurrency | 2.0 | 3.0 | +1.0 |
| Deployment | 3.5 | 4.0 | +0.5 |

Observability maturity: **basic** (level 2/5 on none/basic/structured/contextual/full).

---

## Findings by Sweep

### Sweep 1 — Contracts & Security

**P0 — correctness regressions introduced by remediation**

1. **Idempotency-Key per-attempt UUID** — `src/api/client.ts:17-19`. Every retry (axios, React Query `retry: 1`, or user double-click) gets a fresh key, so the backend cannot dedupe. **Fix:** hoist into `onMutate` closure; reuse across retries; skip the `/auth/login` path so server can't accidentally cache login responses.
2. **`useUpdateFarm` bypasses `useUpdateEntity`** — `src/api/farms.ts:46-60`. No `entityDetailKey` invalidation → stale `useFarm(id)` after edit. **Fix:** `export const useUpdateFarm = () => useUpdateEntity<Farm, UpdateFarmInput>(RESOURCE);` (one line).

**P1 — schema / security boundaries**

3. **No response-shape Zod** at `src/api/_entity.ts:11-19`. **Fix:** `paginatedSchema<T>(itemSchema)` factory, parse inside `fetchEntityList`. Even three resource schemas cover ~80% of read traffic.
4. **FK picker silent truncation** at `src/components/entity-form.tsx:284-286`. `useEntityList(resource, {size:100})` with no overflow indicator. **Fix:** surface "showing first N of M" or paginate via a combobox.
5. **`tw_logged_in` is a UX hint, not a control** — `middleware.ts:12` admits any request with the cookie. **Low-cost fix:** comment that this is a UX hint only; rename to `tw_login_hint`. **Real fix:** httpOnly cookie set server-side at login (needs backend cooperation).
6. **Cookie / JWT TTL drift** — `tokenStorage.ts:31` sets `Max-Age=86400` independent of `claims.exp`. **Fix:** derive `Max-Age` from `claims.exp - now`.

**P2 — cleanup / hygiene**

7. **Imperative twins zero-callers** — `zones.ts:19-37`, `trees.ts`, `sensors.ts`, `water-sources.ts`, `water-switchers.ts`, `irrigation-tasks.ts` (lines 19-44 each). Only `fetchList` is consumed (by the dashboard). **Fix:** delete the rest; replace dashboard imports with `fetchEntityList<T>("…", …)`.
8. **`useFarmStats` empty-string fallback key** — `src/api/farms.ts:64`. **Fix:** `entityChildKey(RESOURCE, "stats", farmName!)` after guard.
9. **Health route shape `{status:"ok"}` is frozen** — `src/app/api/health/route.ts`. Document that the shape is part of the SLA, or switch to dynamic and add `version`/`uptime`.
10. **`safeRedirect` permits encoded slashes** — `/%2F%2Fevil` passes the allowlist; safe in practice (Next router doesn't re-resolve) but harden via decode-then-revalidate.
11. **Middleware drops URL hash** — fragments aren't sent server-side; preserve on the client if deep-links matter.

**Schema-coupling carryovers**

- FK select `Record<string, unknown>` will silently fail on backend rename — generic `T` + `valueKey: keyof T` would catch at compile time.
- `entityChildKey` accepts arbitrary strings — typed union per resource would prevent collisions.
- `Pagination<T>` shape still hardcoded.
- `FarmStats.chart_data` month-name keys unvalidated; locale change on backend breaks chart silently.
- `Sensor.assigned_to_type: string | null` is a discriminator without an enum.

**Security carryovers / new notes**

- localStorage JWT still exfiltrable on XSS (CSP partial mitigation; root cause unchanged).
- `Idempotency-Key` on `/auth/login` — server must not cache the response (token replay).
- `crypto.randomUUID()` guard in `client.ts:17` is redundant on modern Next runtimes — remove for clarity.

---

### Sweep 2 — Code Quality

**P0 — Highest leverage**

1. **Imperative twins zero-callers** (also a Sweep-1 finding) — delete and collapse to thin Facades over `_entity`.
2. **Toast coupling inside reusable components** — `src/components/entity-crud-page.tsx:105-118`, `src/components/entity-table.tsx:88-95`. **Fix:** emit `entity:created`/`entity:errored` events via `eventBus`; a single top-level subscriber renders toasts.
3. **`as never` + 5-generic `EntityCrudPage`** — `src/app/(app)/users/page.tsx:55-93` has 8 casts. **Fix:** split into 3 generics with optional edit overrides; add a `defineField<V>()` helper so the cast lives in one place.
4. **Per-request Idempotency-Key** — mutation-scoped key via `onMutate` (also caught in Sweep 1).
5. **Stringly-typed numeric/boolean form values + `positiveNumber` ×3** — extract to `src/lib/zod-helpers.ts` with `z.coerce.number().int().positive()`; drop `buildInput` where it becomes identity.

**P1 — Tests**

6. New highest-leverage tests:
   - `src/components/entity-form.test.tsx` — render each variant (`text/select/boolean/textarea/fk`); verify Zod errors render, `defaultValues` round-trip, FK options propagate.
   - `src/components/entity-table.test.tsx` — MSW-backed: search → debounce → list refetch; pagination next/prev; delete confirm calls remove + invalidates root key.
   - `src/api/client.test.ts` — real 401 round-trip; assert `Idempotency-Key` per-attempt regression.
   - `middleware.test.ts` — pure unit test; cookieless redirect; `next` param sanitised via `safeRedirect`.
   - `e2e/login-flow.spec.ts` (Playwright) — login → create user → list shows it → logout.
7. Replace `_entity.test.ts`'s private-handler probe with an MSW-driven 401 round trip.
8. Wire `vitest.setup.ts` with MSW + a `renderWithProviders(QueryClient + Toaster)` helper — currently MSW + user-event sit as dead weight.

**P2 — smaller cleanups**

- `HomePage` (`src/app/(app)/page.tsx`, ~370 LOC client god-component) — extract `useDashboardSummaries()`; split into hero/grid/farm-overview.
- No request cancellation on debounced search — thread `AbortSignal` through `_entity.ts:fetchEntityList`.
- `AnyZod = ZodType<any,any>` + double cast in `entity-form.tsx:14-15,104` — encapsulate in a `useZodForm<T>()` helper.
- Telemetry adapter missing — define `src/lib/telemetry.ts` subscribing to `api:error`.
- `useFarmStats` cached by name, not id — rename orphans entry.
- `safeRedirect(pathname)` called twice per render in `require-auth.tsx` — memoise.
- `HANDOFF.md` and `AUDIT.md` at repo root — left in place; user-owned.
- British `capitalised` vs American `Canceled` mix.
- `lucide-react@^1.14.0` — suspicious version; verify it's not actually `^0.x`.
- `entity-form.tsx:14-15` `eslint-disable-next-line` between imports and types — move below imports block.
- `RowActions` not `React.memo`'d — minor at pageSize 20 but cascades when cell rendering grows.

**Style / structural**

- `EntityCrudPage` 14 props + 5 generics — Ousterhout-shallow. **Suggestion:** collapse `createSchema/editSchema/createFields/editFields/createDefaults/toEditDefaults/toCreateInput/toUpdateInput` into two objects: `create: { schema, fields, defaults, toInput }` + `edit?: { schema, fields, toDefaults, toInput }`.
- "create" (CRUD verb) vs "edit" (UX verb) vs "update" naming drift — pick a vocabulary and document.
- `RESOURCE` vs `resource` vs `entity` triple naming — consider `EntityNoun = { resource, singular, title }`.
- `toastDescription` exported (`src/api/errors.ts`) but never imported — both consumers reinvent the same conditional inline.
- `getErrorMessage` exported but unused — dead code.

---

### Sweep 3 — Operations & Infrastructure

**P0**

1. **Observer with no sink** — `QueryProvider` emits `api:error`; nobody subscribes. **Fix:** `src/providers/ObservabilityProvider.tsx` that subscribes and forwards to a telemetry vendor (Sentry/PostHog) or a structured `/api/log` endpoint.
2. **Direct `api.get` paths bypass the bus** — non-401 errors from `fetchFarms` etc. (used in dashboard outside React Query) never emit. **Fix:** emit `api:error` from the axios response interceptor too, before reject.
3. **`/api/health` is `force-static`** → TCP-liveness only, not readiness. **Fix:** drop `force-static`; check `process.uptime() > 1` and optionally a downstream HEAD ping.
4. **Middleware has no `try/catch`** in Edge runtime → any throw 500s the whole site for every request including `/login`. **Fix:** wrap body; fail-open on the cookie check (`NextResponse.next()`).
5. **`PROTECTED_MATCHER` regex duplicates `config.matcher`** in `middleware.ts:5,23` — two sources of truth. **Fix:** rely on `matcher` alone or unit-test the regex.

**P1**

6. **FK picker autofetch × N fields × every dialog open** — `src/components/entity-form.tsx:284-286`. **Fix:** bump `staleTime` for FK lists; consider `queryClient.prefetchQuery` on table mount.
7. **`(app)/page.tsx` is `"use client"` but middleware now gates** — refactor to RSC shell + `<DashboardLiveIsland />` client island. Saves ~30-40 KB gzipped from the dashboard route.
8. **`isRedirecting` reset on `queueMicrotask`** — `client.ts:40-42`. Racy under concurrent 401s. **Fix:** reset on settled re-auth/navigation, not on a microtask.
9. **Per-request Idempotency-Key** — same finding (Memento misapplied — see Sweep 1).
10. **Dev-only CVEs from vitest@2 → vite → esbuild chain** — plan `vitest@4` bump (major version).
11. **Unused devDeps** — `msw` and `@testing-library/user-event` installed with zero references. **Fix:** wire MSW in `vitest.setup.ts` or drop both.
12. **`shadcn` runtime CSS but declared in devDeps** — `src/app/globals.css` does `@import "shadcn/tailwind.css"`. Works because Next build runs with devDeps installed; move to `dependencies` for semantic correctness.

**P2**

- Add `Strict-Transport-Security` header to `securityHeaders` in `next.config.ts`.
- `tokenStorage` cache invalidation in `storage` handler is **listener-gated** — install an unconditional module-level listener on first import.
- `optimizePackageImports` missing `@base-ui/react`.
- No `@next/bundle-analyzer` for verifying perf wins.

---

## Pattern-Based Remediation (cross-sweep)

Five pattern moves close most of the remaining findings:

1. **Ship production sinks for the Observer.** The bus is built; without sinks it's overhead. Register a telemetry sink in a root client provider; route `error.tsx` layer's `console.error` through `emit({ type: "boundary:error", ... })`. Closes Observability dimension and consumes the unused `api:error` channel.
2. **Promote the axios interceptor from single-link to a true Chain of Responsibility.** Ordered handlers: `auth` → `idempotency` (mutation-scoped, skip `/auth/*`) → `correlation-id` → `error-adapter` (calls `toApiError` and emits `api:error` centrally). Fixes per-attempt Idempotency-Key, closes the "non-401 bypass" Observability leak, and removes the `/auth/login` Idempotency-Key gotcha.
3. **Delete the imperative twins; collapse per-feature modules to true Facades.** Removes 25 dead wrappers, forces `useUpdateFarm` to go through `useUpdateEntity` (fixing the cache-stale regression), and removes the divergence vector for future entries.
4. **Zod-backed Adapter at `_entity` boundaries.** One schema registry consumed by `useEntityList` and `FkSelect`. Closes schema-coupling findings (FK rename failure, `chart_data` month keys, sensor discriminator) in one move. Even three resource schemas cover most read traffic.
5. **Unify auth state behind the typed Observer.** Emit `auth:changed` on login/logout; a single subscriber syncs cookie + localStorage + cross-tab `BroadcastChannel`. Replaces the spoofable `tw_logged_in` + `tw-auth-change` window-event channels and closes the TTL drift.

Supporting moves:

6. **Builder for `EntityCrudPage` config.** Collapse 14 props → 2 objects (`create: {...}`, `edit?: {...}`); kills `as never` because field types are inferred from the builder.
7. **Strategy registry per `EntityForm` field variant** — each variant owns `parse/serialize/validate/render`. Removes `positiveNumber` triplication and stringly-typed coercion.
8. **Mediator for user feedback via existing `eventBus`** — reusable components stop calling `toast.*` directly; a top-level subscriber renders toasts. Lets tests assert on emitted events instead of mocking `sonner`.
9. **Provider/Context for auth Singletons** — `isRedirecting`/`claimsCache`/`cachedToken` behind an `AuthSession` provider with a test double. Makes redirect-loop + Idempotency-Key behaviour assertable and removes the Node-Buffer-in-jsdom workaround in `auth.test.ts`.
10. **Circuit Breaker at middleware + split health Strategy** — wrap middleware body; `/api/health/live` (static) vs `/api/health/ready` (downstream ping).

---

## Top 7 Next Actions (priority-ordered)

1. **Mutation-scoped Idempotency-Key** in `onMutate`; skip `/auth/login`.
2. **`useUpdateFarm = () => useUpdateEntity(RESOURCE);`** — one-line fix at `src/api/farms.ts:46-60`.
3. **Delete imperative twins** in 6 per-feature modules; collapse to true Facades.
4. **Wrap middleware in `try/catch`**, drop `force-static` on `/api/health`, add `Strict-Transport-Security`.
5. **Promote axios interceptor to a real Chain of Responsibility** (auth → idempotency → correlation → error-adapter).
6. **Ship one production sink for `api:error`** — a structured JSONL `/api/log` endpoint or a Sentry/PostHog adapter.
7. **Builder + Strategy registry refactor** of `EntityCrudPage` / `EntityForm` to kill `as never`, `AnyZod`, and `buildInput` ×8 — same change unlocks the form/table integration tests that MSW + user-event are sitting idle for.

---

## What Changed Since the First Audit

**Closed (verified absent in this pass)**

- God CRUD pages → declarative `EntityCrudPage` configs.
- 9 inline `getErrorMessage` copies → all sites use `toApiError`.
- Dual Repository (`users.ts`/`farms.ts` legacy) → thin delegates.
- `queries.ts` deleted; single key Registry in `_entity.ts`.
- `useApiErrorHandler` dead hook → deleted.
- `next-themes` unused dep → removed.
- `useDebounced` → moved to `src/hooks/`.
- HIGH CVE `GHSA-26hh-7cqf-hhc6` → patched via next 16.2.6.
- No `error.tsx` / `global-error.tsx` → all three layers added.
- Per-render `jwtDecode` + `JSON.parse(localStorage)` → Flyweight + token cache.
- 401 → `window.location.href` hard nav → event-bus + `router.replace`.
- No `HEALTHCHECK` / `/api/health` → both added.
- No security headers → CSP + X-Frame-Options + Referrer-Policy + Permissions-Policy.
- No `engines` / `.nvmrc` → added.

**Still open or newly noticed**

- Per-request Idempotency-Key (new regression).
- `useUpdateFarm` bespoke (new regression — broke detail-cache invalidation).
- Imperative twins in 6 modules (latent, but already drifting).
- Observer has no `api:error` sink (built, not finished).
- Direct `api.get` paths bypass the bus.
- `tw_logged_in` cookie is a UX hint, not auth.
- Cookie / JWT TTL drift.
- `/api/health` `force-static` (TCP liveness only).
- Middleware no `try/catch`.
- `as never` × 8 in `users/page.tsx`.
- Stringly-typed form values + `positiveNumber` ×3.
- FK picker fires N queries per dialog; no shared cache / no overflow handling.
- MSW + `@testing-library/user-event` installed-but-unused.
- Dashboard fan-out (deferred — backend).
- HomePage 370 LOC god-component still client-shelled despite middleware gate.
- No telemetry adapter / Sentry pick.
- No mutation retry policy.
- No per-route response Zod (deferred — architectural).
- httpOnly cookie auth (deferred — backend).

---

*Generated 2026-05-15 by re-running `/sweep1` + `/sweep2` + `/sweep3` against the post-remediation codebase. Original findings + resolution markers live in `AUDIT.md`.*
# FWC Frontend Rewrite — Handoff Context

This file captures the full context of the rewrite so a fresh Claude Code session in this project can pick up where we left off.

## What we're building

A from-scratch rewrite of the **Agri Smart / FWC** smart-farm management app, originally built in Quasar v2 + Vue 3 + Vuex. The old codebase lives at `/home/souhail/Desktop/personal/fwc-front` — kept around for reference only; **do not** edit it. Reasons for the rewrite: Quasar v3→v4 migration was painful, Vuex was dropped from Quasar v4, the old code is hard to reason about.

**New stack:**
- Next.js 16 (App Router, src/ dir, Turbopack)
- React 19
- TypeScript 5
- Tailwind v4 + shadcn/ui (New York style, neutral)
- TanStack Query for server state
- react-hook-form + zod for forms
- axios for HTTP (NOT fetch — interceptors needed for JWT + 401 redirect)
- jwt-decode for token claims
- lucide-react for icons

**Backend:** FastAPI (separate repo, currently runs at `http://localhost:8080`). Auth is JWT bearer, token stored in localStorage under key `"access"` as JSON `{token, ...}`. Endpoints under `/auth/login/`, `/auth/token/verify/`, plus REST resources at `/{plural}/` (e.g. `/users/`, `/zones/`, `/farms/`).

**v1 build target:** **Web SPA only**, fully responsive (covers tablets/phones via browser). Electron and Capacitor were used in the old app but explicitly skipped for v1. Add later if needed.

**Containerized from day 1:** Dockerfile + docker-compose.yml expected (not yet written — pending).

## What's already done

### Scaffolding
- `npx create-next-app@latest` with TS + Tailwind + App Router + src/ + `@/*` alias
- Versions: Next 16.2.5, React 19.2.4, Tailwind v4, TS 5
- shadcn initialized with defaults (`npx shadcn@latest init -d`)
- shadcn components added: button, input, label, card, form, sonner, dialog, sheet, dropdown-menu, table, select, separator, skeleton, badge, avatar, tabs

### Files written
- `src/lib/api.ts` — axios instance with `NEXT_PUBLIC_API_BASE_URL` baseURL, request interceptor (injects `Authorization: Bearer ${token}` from localStorage), response interceptor (on 401: clears token + redirects to `/login?redirect=...`). Exports `getStoredToken`, `setStoredToken`, `clearStoredToken`.
- `src/lib/auth.ts` — `login(payload)`, `logout()`, `getCurrentUserId()` (decodes JWT, checks `exp` for expiry), `isAuthenticated()`.
- `src/components/providers.tsx` — `<Providers>` client component wrapping QueryClientProvider + Sonner Toaster + RQ Devtools (dev only). `staleTime: 30s`, `refetchOnWindowFocus: false`, `retry: 1`.

### Dependencies installed
Production: `@tanstack/react-query`, `@tanstack/react-query-devtools`, `axios`, `react-hook-form`, `zod`, `@hookform/resolvers`, `lucide-react`, `jwt-decode`.

## What's next (TODO, in order)

1. **Wire `<Providers>` into `src/app/layout.tsx`** — wrap `{children}`. Add `font-sans` and base body classes if needed.
2. **`.env.local`** — `NEXT_PUBLIC_API_BASE_URL=http://localhost:8080` (no trailing slash).
3. **Login page** — `src/app/(auth)/login/page.tsx` using shadcn `Card` + `Form` + `Input` + react-hook-form + zod schema (`username` non-empty, `password` non-empty). On success: `router.push(searchParams.get('redirect') ?? '/')`. On error: sonner toast. Use the `login()` helper from `src/lib/auth.ts`.
4. **Auth guard** — `src/middleware.ts` checking for the access token via cookie OR a client wrapper component. **Note:** localStorage isn't readable in middleware — either move the token to an httpOnly cookie (preferred but requires backend change) OR use a client-side `<RequireAuth>` wrapper that calls `isAuthenticated()` in a `useEffect` and redirects. **Recommended for v1:** client-side wrapper, since changing the token storage is a backend concern.
5. **App layout** — `src/app/(app)/layout.tsx` with sidebar (shadcn `Sheet` on mobile, fixed sidebar on `md+`), header with user dropdown (logout). Sidebar nav items match the 8 domain pages: Home, Farm, Zones, Trees, Sensors, Water sources, Water switchers, Irrigation tasks, Users.
6. **Generic CRUD layer:**
   - `src/lib/hooks/use-entity-list.ts` — `useEntityList<T>(resource, params)` returns paginated TanStack Query result. URL pattern: `${resource}/?page=${page}` (matches old EntityListModule).
   - `src/lib/hooks/use-entity.ts` — `useEntity<T>(resource, id)`, `useCreateEntity`, `useUpdateEntity`, `useDeleteEntity`. Mutations invalidate the matching list query key.
   - `src/components/entity-table.tsx` — generic CRUD table with search, pagination, action menu per row, delete confirmation dialog. Mobile: card list. Desktop: shadcn Table.
   - `src/components/entity-form.tsx` — generic form built on react-hook-form, takes a zod schema + field config, renders shadcn form fields.
7. **First domain page: Users** (`src/app/(app)/users/page.tsx`) — proves the generic CRUD flow end-to-end. Then replicate for zones, trees, sensors, water-sources, water-switchers, irrigation-tasks.
8. **Farm page** — Leaflet map (use `react-leaflet`) + Recharts water consumption chart + 3 KPI cards.
9. **Containerization:**
   - `Dockerfile` — multi-stage. Stage 1 deps (cached layer). Stage 2 build with `next build`. Stage 3 runner using `output: 'standalone'` (must add to `next.config.ts`). Non-root user.
   - `.dockerignore` — node_modules, .next, .env*, .git, *.md
   - `docker-compose.yml` — frontend service. Optionally include backend reference (FastAPI lives at `/home/souhail/Desktop/personal/farm-watch-commander` based on parent dir listing).
10. **Polish:** loading skeletons for tables/forms, empty states, error boundaries.

## Old app domain reference

For the resource list and what each page does — already mapped in detail. Quick summary:

| Resource | URL | Old page | Notable |
|----------|-----|----------|---------|
| users | `/users/` | UsersPage | Role badges (5), only superusers can edit |
| farm | `/farms/` | FarmPage | Read-only, Leaflet map + water consumption chart |
| zones | `/zones/` | ZonePage | Stub — nested routes |
| trees | `/trees/` | TreePage | Variety/age stats |
| sensors | `/sensors/` | SensorPage | Assigned/unassigned counters |
| water-sources | `/water_sources/` (verify pluralization with backend) | WaterSourcePage | Same |
| water-switchers | `/water_switchers/` (verify) | WaterSwitcherPage | Same, has barcode-reader integration |
| irrigation-tasks | `/irrigation_tasks/` | IrrigationTasksPage | Stats chart |

The old app had a generic `EntityModule`/`EntityListModule` Vuex pattern — `src/store/Entity/` in the old codebase. The new generic CRUD hooks should follow the same shape (resource name → URL, paginated list, single get, create, update, delete).

## Known gotchas from the old app

- **Backend uses trailing slashes** — POST to `/auth/login/` returns 307 redirect to `/auth/login` without slash. Axios follows by default; just be aware.
- **Backend port confusion** — the FastAPI server runs on `:8080`, not `:8000`. Old `.env` had it wrong.
- **CORS** — backend currently sends `Access-Control-Allow-Origin: *` with no `allow-credentials: true` for the bearer-only flow. Don't set `withCredentials` on the axios client.
- **JWT claim shape** — `user_id` (snake_case) inside the JWT, plus standard `exp`. Set in `JwtClaims` type in `src/lib/auth.ts`.
- **Quasar's `is_superuser` permission flag** is the only RBAC in the old app — no role-based route guards. Replicate with a simple flag on the user object.

## How to resume

Open this folder in PyCharm. Start a new Claude Code session. First message to the new agent:

> Read `HANDOFF.md` and continue from "What's next" step 1 (wire Providers into layout.tsx). Don't re-audit the old project; everything you need is in this doc. Backend runs at http://localhost:8080.

That's it.
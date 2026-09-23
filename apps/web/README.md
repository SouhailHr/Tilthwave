# Tilthwave web

The farm dashboard. Next.js 16 (App Router, `src/`, Turbopack) · React 19 · TypeScript ·
Tailwind v4 + shadcn/ui (base-ui) · TanStack Query · react-hook-form + Zod · axios · Vitest.

It runs as the `web` service of the stack (`make up` at the repo root, http://localhost:3000).
Everything below is for working on it directly.

> This Next.js version differs from older training data; `AGENTS.md` points agents at the
> bundled docs in `node_modules/next/dist/docs/` before they write code.

## Development

```bash
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080 npm run dev   # against the docker API
npm run lint          # eslint, incl. import/order: imports at the top, grouped npm / @/ / relative, alphabetised
npm test              # vitest run  (npm run test:watch)
npm run build         # next build (standalone output, what the Dockerfile ships)
```

`NEXT_PUBLIC_API_BASE_URL` is baked in at build time. Unset, the client falls back to the current
origin, which only works behind a proxy that serves the API on the same host.

## Layout

```
middleware.ts             per-request CSP nonce; redirects to /login when the tw_access cookie is
                          absent (fast path only)
src/
  app/
    (auth)/               login, forgot-password, reset-password
    (app)/                the shell: dashboard, farms, zones, trees, sensors, water-sources,
                          water-switchers, irrigation-tasks, users, settings
    api/health            liveness for compose
    error.tsx, global-error.tsx
  api/                    axios client + one module per resource (useX hooks); entity-queries.ts is
                          the generic list / get / create / update / delete layer
  components/             app-shell, require-auth, entity-crud-page / entity-form / entity-table,
                          dashboard cards, ui/ (shadcn)
  providers/              QueryProvider, ObservabilitySink
  hooks/, lib/, utils/    useDebounced, useDisclosure, eventBus, status-ui (one status vocabulary per
                          resource), password-schema (the API's rule, once), dates
  types/                  hand-written API types, one file per resource
```

Every resource page is `EntityCrudPage` plus a column list, a Zod schema and a field config; the
generic layer handles pagination, search, the FK picker, create/edit dialogs and delete
confirmation. Lists come newest-first from the API.

## Auth

The session is an httpOnly cookie set by the API; the browser never sees the token.

- `useLogin` posts to `/auth/login` with `use_cookie=true`; the API sets `tw_access` (httpOnly)
  and `tw_csrf` (readable).
- The axios client sends `withCredentials` and copies `tw_csrf` into `X-CSRF-Token` on every
  non-GET request. A 401 anywhere but `/auth/me` emits `auth:expired`, which clears the session
  query and redirects to `/login?redirect=...`.
- `RequireAuth` asks `/auth/me` (`useSession`) and renders nothing until it has an answer; it
  redirects only on a confirmed `null` session, so a refresh never bounces a logged-in user.
- The reset page reads its token from the link once and removes it from the URL (history,
  Referer). Changing the email in Settings asks for the current password.
- `middleware.ts` only checks that the cookie exists, to skip rendering protected pages for
  anonymous visitors; the server-backed check above is the real gate.
- Settings (`/settings`) lists the signed-in sessions (`/account/sessions`, with sign-out per
  device and everywhere else) and changes the password through `/account/password`; forgot/reset password
  go through `/auth/password/forgot` and `/auth/password/reset`. Any password change invalidates
  every other session for that user (the API fingerprints the hash into the token).

## Brand

The brand kit lives in `public/brand` (SVG masters, reverse-mark PNGs for icons) and
`src/app/tokens.css` (loam, loam-deep, furrow, shoot, amber, sage, radii), imported once by
`globals.css`, which builds the shadcn variables and the `bg-loam` / `text-furrow` / `bg-shoot`
utilities from it. Rules worth remembering: the wordmark is always the lowercase `tilthwave`
lockup SVG, not live text (the sign-in card is the one approved exception); amber is a signal
colour for live and alert states, never a fill; shoot text fails contrast on sage, so links are
furrow on light and shoot on dark. The sign-in screens draw the animated field with
`src/lib/field-background.ts` (a still frame under reduced motion, stopped on unmount).

## Dates

The API returns ISO 8601 timestamps with a UTC offset (`2026-09-15T16:06:56.266864+00:00`);
`utils/dates.ts` parses them (and the older naive form, as UTC) and renders local time to the
second. Use it rather than `new Date(value)` so the naive form is never read as local time.

## Tests

Vitest with jsdom and Testing Library, next to the code (`*.test.ts(x)`). Covered: the auth
hooks and the axios client (through a fake adapter: CSRF header, the one-redirect guard on
simultaneous 401s), the generic entity layer and its invalidation, error mapping, `RequireAuth`,
the CRUD page shell, the login, forgot and reset pages, Settings (email re-auth, sessions), the
observability sink, `useDebounced`, dates, and the dropdown menu (regression: a
`DropdownMenuLabel` must sit inside a `DropdownMenuGroup`, or base-ui throws when the menu opens).

`import * as z from "zod"`, never `import { z }`: the named `z` re-export keeps zod's 63 locales
in every route's bundle (40 KB gz); the namespace import lets Turbopack drop them.

What is left to do here is in `../../docs/BACKLOG.md`.

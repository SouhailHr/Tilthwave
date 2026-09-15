# Deploy

Root orchestration for running the whole Tilthwave stack together (backend
services + broker + simulator + web + reverse proxy). Each app also ships its
own compose for standalone dev; this directory is for the combined demo/prod
stack behind `tilthwave.hannibyte.com`.

- `docker-compose.yml` — STARTER skeleton wiring all apps by build context.
  Complete the TODOs (env, healthchecks, reverse proxy) before relying on it.
  This corresponds to the roadmap's Milestone 2 `docker-compose.demo.yml`.
- `.env.example` — deployment env template. Copy to `.env` and fill in.

Reverse proxy: Caddy or Traefik terminates TLS for `tilthwave.hannibyte.com`
and routes `/` → web and `/api` → backend API. Add it as a service here.

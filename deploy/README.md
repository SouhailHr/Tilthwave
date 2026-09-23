# deploy/

The single orchestration for the whole stack:

- `docker-compose.yml`: every service, shaped for production: registry images, no published host
  ports, a `db-backup` service. This is the file a production host runs.
- `docker-compose.local.yml`: layered on top for development: `build:` from this checkout and the
  `127.0.0.1` host ports.
- `.env.example` (every variable, generated secrets left blank) and `gen-env.sh` (creates `.env`
  with real secrets).

Drive it from the repository root:

```bash
make env     # once
make up      # build + start (both files); make logs / make ps / make down / make reset
make db-dump # ad-hoc pg_dump into deploy/dumps/ (gitignored) — run it before `make migrate` on real data
```

## Backups

`db-backup` runs `pg_dump` into the `pgbackups` volume every `BACKUP_INTERVAL_HOURS` (24) and
deletes dumps older than `BACKUP_KEEP_DAYS` (14). The volume lives on the host; copy it off the
machine if the machine itself is the risk. Restore into a running stack:

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec db-backup ls -1 /backups
docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec db-backup \
  sh -c 'gunzip -c /backups/<file>.sql.gz' | docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec -T db psql -U postgres tilthwave
```

`.env.example` documents each variable. Outgoing mail (`SMTP_*`) is optional: left blank, the API
logs password-reset links instead of sending them.

## Releases

A git tag `vX.Y.Z` is a production release: `.github/workflows/release.yml` builds the backend,
simulator and web images from the tagged commit and pushes them to
`ghcr.io/souhailhr/tilthwave-{backend,simulator,web}` as `vX.Y.Z`, `X.Y.Z` and `sha-<commit>`.
Nothing is published on ordinary pushes; `make up` keeps building from the checkout
(`TILTHWAVE_TAG=local`).

The web bundle bakes the public API URL in, so the workflow reads it from the repository variable
`NEXT_PUBLIC_API_BASE_URL` (`gh variable set NEXT_PUBLIC_API_BASE_URL --body https://...`) and
refuses to build the web image until it is set.

Without Coolify, on a plain docker host (the repository is private, so its packages are too:
`docker login ghcr.io` with a token that has `read:packages`):

```bash
git fetch --tags && git checkout vX.Y.Z                       # the compose file of that release
sed -i 's/^TILTHWAVE_TAG=.*/TILTHWAVE_TAG=vX.Y.Z/' deploy/.env
make deploy                                                   # pull, then up -d (production file only)
```

Rolling back is the same commands with the previous tag.

## Coolify

Production runs on Coolify, which supplies the TLS proxy (Traefik + Let's Encrypt), the
environment, and deploys from git. One-time setup:

1. **New resource → Private Repository (with GitHub App)**, this repository, branch `main`, build
   pack **Docker Compose**, base directory `/`, compose file `/deploy/docker-compose.yml`.
   The file names registry images and has no `build:`, so Coolify pulls; it does not build.
2. **Registry access**: the repository is private, so its packages are too. On the Coolify server
   run `docker login ghcr.io` once with a token that has `read:packages` (Coolify runs docker as
   that host user).
3. **Environment**: Coolify lists every `${VAR}` the file references. Fill the required ones
   (`POSTGRES_PASSWORD`, `API_SECRET_KEY`, `ADMIN_PASSWORD`, `SIM_PASSWORD`; generate them like
   `gen-env.sh` does) and the production values from the checklist below. `TILTHWAVE_TAG` is set
   by the release workflow.
4. **Domains**: on the `web` service set `https://<app domain>:3000`, on the `api` service
   `https://<api domain>:8080` (the `:port` tells Coolify which container port to route; the
   public side stays 443). Expose nothing else: the Redpanda console has no authentication.
5. **Turn auto-deploy on push off** for this resource: releases are tag-driven (below).
6. In GitHub, set the repository variables `COOLIFY_URL` (e.g. `https://coolify.example.com`) and
   `COOLIFY_APP_UUID` (from the resource's URL) and the secret `COOLIFY_TOKEN` (Coolify → Keys &
   Tokens, an API token with deploy rights).

`migrate`, `seed` and `broker-init` exit on purpose (`restart: "no"`); Coolify excludes such
services from the application's health verdict. `web` and `api` carry healthchecks Coolify reads. Those healthchecks are liveness only (`/health`, `/api/health`): a database outage does not
make the containers unhealthy, so nothing restarts them for a problem a restart cannot fix.
Readiness, for monitoring, is `/health/ready` on the API and `/api/health/ready` on the web.

Each `vX.Y.Z` tag then runs `release.yml`: images are built and pushed, `TILTHWAVE_TAG` is set
on the Coolify application through its API, and a deploy is triggered. Rolling back is re-running
the workflow on the previous tag (Actions → Release images → the old tag), or setting
`TILTHWAVE_TAG` by hand in Coolify and redeploying.

## Production checklist

Production adds a TLS reverse proxy in front of `web` and `api` and publishes nothing else. The
proxy config is not in this repo yet. In `.env`:

| Variable | Production value |
|---|---|
| `BIND_ADDR` | the proxy-facing address; keep db, broker and console unpublished |
| `API_CORS_ORIGINS` | the web app's public origin only |
| `NEXT_PUBLIC_API_BASE_URL` | the API's public URL (baked into the web image at build time) |
| `API_WEB_BASE_URL` | the web app's public URL (password-reset links) |
| `FORWARDED_ALLOW_IPS`, `API_TRUSTED_PROXIES` | the proxy's address, so client IPs and the login rate limit are right |
| `API_COOKIE_SECURE` | `true` (session cookies only over TLS) |
| `API_COOKIE_DOMAIN` | set only when web and API are on different subdomains |
| `API_DOCS_ENABLED` | `false` |
| `SMTP_HOST` and the other `SMTP_*` | a real mail relay, or password reset only works from the logs |
| `UVICORN_WORKERS` | `1`, or move login rate limiting to the proxy |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | the farm's **owner** account (only an owner appoints admins) |
| `API_SESSION_IDLE_MINUTES`, `API_SESSION_MAX_HOURS` | `60` and `12` unless the farm office needs longer; sessions are server-side, so logout and "sign out everywhere" are immediate |

`Strict-Transport-Security` is sent by the apps themselves (web always, API when
`API_COOKIE_SECURE=true`). The broker has no TLS or auth and must stay on the compose network.

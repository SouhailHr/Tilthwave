# deploy/

The single orchestration for the whole stack: `docker-compose.yml` (all services), `.env.example`
(every variable, with the generated secrets left blank), and `gen-env.sh` (creates `.env` with real
secrets). Drive it from the repository root:

```bash
make env     # once
make up      # build + start; make logs / make ps / make down / make reset
make db-dump # pg_dump into deploy/dumps/ (gitignored) — run it before `make migrate` on real data
```

`.env.example` documents each variable. Outgoing mail (`SMTP_*`) is optional: left blank, the API
logs password-reset links instead of sending them.

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

Add `Strict-Transport-Security` at the proxy. The broker has no TLS or auth and must stay on the
compose network.

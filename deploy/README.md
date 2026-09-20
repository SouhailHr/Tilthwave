# deploy/

The single orchestration for the whole stack: `docker-compose.yml` (all services), `.env.example`
(every variable, with the generated secrets left blank), and `gen-env.sh` (creates `.env` with real
secrets). Drive it from the repository root:

```bash
make env     # once
make up      # build + start; make logs / make ps / make down / make reset
make db-dump # pg_dump into deploy/dumps/ (gitignored) — run it before `make migrate` on real data
```

Production adds a TLS reverse proxy in front of `web` and `api` and publishes nothing else. Set
`API_CORS_ORIGINS`, `NEXT_PUBLIC_API_BASE_URL`, `FORWARDED_ALLOW_IPS` (the proxy's address) and
`BIND_ADDR` accordingly in `.env`.

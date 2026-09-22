# Tilthwave — full local stack (see deploy/docker-compose.yml)
COMPOSE := docker compose -f deploy/docker-compose.yml --env-file deploy/.env

.DEFAULT_GOAL := help
help: ## List targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---- Lifecycle ----

env: ## Create deploy/.env with generated secrets (no-op if it exists)
	@./deploy/gen-env.sh

up: env ## Build and start everything in the background
	$(COMPOSE) up -d --build

up-fg: env ## Build and start everything in the foreground
	$(COMPOSE) up --build

deploy: env ## Pull the release images named by TILTHWAVE_TAG in deploy/.env and start without building
	@tag=$$(sed -n 's/^TILTHWAVE_TAG=//p' deploy/.env); case "$$tag" in ""|local) echo "deploy/.env: set TILTHWAVE_TAG to a release tag (v1.2.3) first"; exit 1;; esac
	$(COMPOSE) pull
	$(COMPOSE) up -d --no-build

down: ## Stop and remove containers (data volumes kept)
	$(COMPOSE) down

reset: ## Stop everything and wipe DB + broker volumes (DESTRUCTIVE, asks first)
	@read -p "This deletes all Tilthwave data volumes. Type 'yes' to continue: " answer; \
	[ "$$answer" = "yes" ] && $(COMPOSE) down -v || echo "aborted"

ps: ## Service status
	$(COMPOSE) ps

logs: ## Follow all logs (make logs s=api for one service)
	$(COMPOSE) logs -f --tail=100 $(s)

# ---- Data ----

seed: ## Re-run the demo seed (idempotent)
	$(COMPOSE) run --rm seed

migrate: ## Apply pending migrations
	$(COMPOSE) run --rm migrate

migration-create: ## Autogenerate a migration (m="message")
	$(COMPOSE) run --rm migrate alembic revision --autogenerate -m "$(m)"

create-admin: ## Bootstrap an extra admin (ADMIN_* env vars or prompts)
	$(COMPOSE) run --rm -it seed python /backend/app/infrastructure/scripts/create_admin.py

psql: ## Open psql on the stack database
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

db-dump: ## pg_dump the database to deploy/dumps/<timestamp>.sql
	@mkdir -p deploy/dumps && $(COMPOSE) exec -T db sh -c 'pg_dump -U "$$POSTGRES_USER" "$$POSTGRES_DB"' > deploy/dumps/$$(date +%Y%m%d-%H%M%S).sql && ls -1 deploy/dumps | tail -1

# ---- Development ----

test: ## Run the backend and simulator test suites
	cd apps/backend && uv run pytest -q
	cd apps/simulator && uv run ruff check app

lint: ## Lint all Python apps
	cd apps/backend && uv run ruff check app tests
	cd apps/simulator && uv run ruff check app

.PHONY: help env up up-fg down reset ps logs seed migrate migration-create create-admin psql db-dump test lint

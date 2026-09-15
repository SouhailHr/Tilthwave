# Tilthwave - dev workflow
# Usage: make <target>   (run `make help` to list targets)

# ---- Container names (must match docker-compose.yml) ----
DB_CONTAINER          := tilthwave-db
API_CONTAINER         := tilthwave-api
STREAMER_CONTAINER    := tilthwave-streamer
FLOW_RUNNER_CONTAINER := tilthwave-flow-runner
NETWORK               := tilthwave-network
COMPOSE               := docker compose

.DEFAULT_GOAL := help

help:
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---- Bootstrap ----

network: ## Create the external docker network if missing
	@docker network inspect $(NETWORK) >/dev/null 2>&1 || docker network create $(NETWORK)

env-check: ## Fail loudly if .env is missing
	@test -f .env || (echo "ERROR: .env not found at repo root" && exit 1)

# ---- Lifecycle ----

up: env-check network ## Build and start all services in background
	$(COMPOSE) up -d --build

up-fg: env-check network ## Build and start all services in foreground
	$(COMPOSE) up --build

down: ## Stop and remove containers
	$(COMPOSE) down

restart: down up ## Restart the whole stack

up-api: env-check network ## Start only db + api
	$(COMPOSE) up -d --build db api

up-streamer: env-check network ## Start only the streamer (broker must already be up)
	$(COMPOSE) up -d --build streamer

up-flow: env-check network ## Start only the flow runner
	$(COMPOSE) up -d --build flow_runner

ps: ## List running services for this project
	$(COMPOSE) ps

# ---- Logs ----

logs: ## Follow logs for all services
	$(COMPOSE) logs -f

logs-tail: ## Follow last 100 lines for all services
	$(COMPOSE) logs -f --tail=100

api-logs: ## Follow API logs
	docker logs -f $(API_CONTAINER)

db-logs: ## Follow DB logs
	docker logs -f $(DB_CONTAINER)

streamer-logs: ## Follow Streamer logs
	docker logs -f $(STREAMER_CONTAINER)

flow-logs: ## Follow Flow Runner logs
	docker logs -f $(FLOW_RUNNER_CONTAINER)

# ---- Shells ----

api-bash: ## Shell into the API container
	docker exec -it $(API_CONTAINER) /bin/bash

db-bash: ## Shell into the DB container
	docker exec -it $(DB_CONTAINER) /bin/bash

streamer-bash: ## Shell into the Streamer container
	docker exec -it $(STREAMER_CONTAINER) /bin/sh

flow-bash: ## Shell into the Flow Runner container
	docker exec -it $(FLOW_RUNNER_CONTAINER) /bin/bash

db-psql: ## Open psql against the project DB
	docker exec -it $(DB_CONTAINER) psql -U postgres -d tilthwave

# ---- Migrations (alembic, run inside the api container) ----

migrate: ## Apply all pending migrations
	docker exec -it $(API_CONTAINER) alembic upgrade head

migration-create: ## Autogenerate a migration. Prompts for message
	@read -p "Migration message: " message; \
	docker exec -it $(API_CONTAINER) alembic revision --autogenerate -m "$$message"

migration-rollback: ## Rollback the latest migration
	docker exec -it $(API_CONTAINER) alembic downgrade -1

migration-fresh: ## Drop everything and re-apply (DESTRUCTIVE)
	docker exec -it $(API_CONTAINER) sh -c "alembic downgrade base && alembic upgrade head"

migration-status: ## Show current revision
	docker exec -it $(API_CONTAINER) alembic current

migration-history: ## Show migration history
	docker exec -it $(API_CONTAINER) alembic history

# ---- Seed / admin ----

create-admin: ## Bootstrap an admin user (prompts or reads ADMIN_* env vars)
	docker exec -it $(API_CONTAINER) python /fwc/app/infrastructure/scripts/create_admin.py

seed: ## Seed deterministic demo data (farm, zones, sensors, switchers, initial readings)
	docker exec $(API_CONTAINER) python /fwc/app/infrastructure/scripts/seed_data.py

# ---- DB dump / restore ----

db-dump: ## pg_dump the database into POSTGRES_DUMP_PATH
	docker exec -it $(API_CONTAINER) python /fwc/app/infrastructure/scripts/dump_db.py

db-restore: ## Drop schema and restore from POSTGRES_DUMP_PATH (DESTRUCTIVE)
	docker exec -it $(API_CONTAINER) python /fwc/app/infrastructure/scripts/restore_db.py

# ---- Cleanup ----

clean: down ## Stop the stack and prune unused docker resources
	docker system prune -f

superclean: clean ## Also drop the postgres volume (DESTRUCTIVE - wipes all data)
	docker volume rm tilthwave_pgdata 2>/dev/null || true

.PHONY: help network env-check up up-fg down restart up-api up-streamer up-flow ps \
	logs logs-tail api-logs db-logs streamer-logs flow-logs \
	api-bash db-bash streamer-bash flow-bash db-psql \
	migrate migration-create migration-rollback migration-fresh migration-status migration-history \
	create-admin seed db-dump db-restore clean superclean
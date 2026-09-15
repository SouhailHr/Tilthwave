# Broker Sandbox - dev workflow
# Usage: make <target>   (run `make help` to list targets)

# ---- Container names (must match docker-compose.yml) ----
BROKER_CONTAINER  := farm-sandbox-redpanda
CONSOLE_CONTAINER := farm-redpanda-console
NETWORK           := farm-network-dev
VOLUME            := brokersandbox_redpanda
COMPOSE           := docker compose

.DEFAULT_GOAL := help

help:
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---- Bootstrap ----

network: ## Create the external docker network if missing
	@docker network inspect $(NETWORK) >/dev/null 2>&1 || docker network create $(NETWORK)

# ---- Lifecycle ----

up: network ## Start broker + console in background
	$(COMPOSE) up -d

up-fg: network ## Start broker + console in foreground
	$(COMPOSE) up

down: ## Stop and remove containers
	$(COMPOSE) down

restart: down up ## Restart the stack

ps: ## List running services for this project
	$(COMPOSE) ps

# ---- Logs ----

logs: ## Follow logs for all services
	$(COMPOSE) logs -f

logs-tail: ## Follow last 100 lines for all services
	$(COMPOSE) logs -f --tail=100

broker-logs: ## Follow broker logs
	docker logs -f $(BROKER_CONTAINER)

console-logs: ## Follow console logs
	docker logs -f $(CONSOLE_CONTAINER)

# ---- Shells ----

broker-bash: ## Shell into the broker container
	docker exec -it $(BROKER_CONTAINER) /bin/bash

console-bash: ## Shell into the console container
	docker exec -it $(CONSOLE_CONTAINER) /bin/sh

# ---- Broker helpers (rpk) ----

cluster-info: ## Show cluster info
	docker exec -it $(BROKER_CONTAINER) rpk cluster info

cluster-health: ## Show cluster health
	docker exec -it $(BROKER_CONTAINER) rpk cluster health

topic-list: ## List all topics
	docker exec -it $(BROKER_CONTAINER) rpk topic list

topic-describe: ## Describe a topic. Prompts for name
	@read -p "Topic name: " name; \
	docker exec -it $(BROKER_CONTAINER) rpk topic describe "$$name"

topic-create: ## Create a topic. Prompts for name and partitions
	@read -p "Topic name: " name; \
	read -p "Partitions [1]: " parts; \
	parts=$${parts:-1}; \
	docker exec -it $(BROKER_CONTAINER) rpk topic create "$$name" -p "$$parts"

topic-delete: ## Delete a topic. Prompts for name
	@read -p "Topic name to delete: " name; \
	docker exec -it $(BROKER_CONTAINER) rpk topic delete "$$name"

produce: ## Produce messages interactively. Prompts for topic
	@read -p "Topic: " topic; \
	docker exec -it $(BROKER_CONTAINER) rpk topic produce "$$topic"

consume: ## Consume N messages. Prompts for topic and count
	@read -p "Topic: " topic; \
	read -p "Number of messages [10]: " num; \
	num=$${num:-10}; \
	docker exec -it $(BROKER_CONTAINER) rpk topic consume "$$topic" --num "$$num"

# ---- Cleanup ----

clean: down ## Stop the stack and prune unused docker resources
	docker system prune -f

superclean: clean ## Also drop the broker volume (DESTRUCTIVE - wipes all data)
	docker volume rm $(VOLUME) 2>/dev/null || true

.PHONY: help network up up-fg down restart ps \
	logs logs-tail broker-logs console-logs \
	broker-bash console-bash \
	cluster-info cluster-health topic-list topic-describe topic-create topic-delete produce consume \
	clean superclean
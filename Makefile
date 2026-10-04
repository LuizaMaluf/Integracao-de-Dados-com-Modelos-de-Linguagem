.PHONY: install test lint up down dbt-deps dbt-run dbt-test

# Carrega o .env da raiz (se existir) para os comandos dbt
DBT = set -a; [ -f .env ] && . ./.env; set +a; dbt
DBT_ARGS = --project-dir dbt --profiles-dir dbt --target dev

# ── Python ───────────────────────────────────────────────────────
install:
	pip install -e ".[postgres,dev]"

test:
	pytest

lint:
	ruff check src tests

# ── PostgreSQL local (testes `pg` e dbt) ─────────────────────────
up:
	docker compose up -d

down:
	docker compose down

# ── dbt ──────────────────────────────────────────────────────────
dbt-deps:
	$(DBT) deps $(DBT_ARGS)

dbt-run:
	$(DBT) run $(DBT_ARGS)

dbt-test:
	$(DBT) test $(DBT_ARGS)

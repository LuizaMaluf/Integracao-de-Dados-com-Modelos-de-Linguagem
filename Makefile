.PHONY: install test lint up down init logs bucket airflow-ui minio-ui dbt-generate dbt-deps dbt-run dbt-test

# Carrega o .env da raiz (se existir) para os comandos dbt
DBT = set -a; [ -f .env ] && . ./.env; set +a; dbt
DBT_ARGS = --project-dir dbt --profiles-dir dbt --target dev

# ── Python ───────────────────────────────────────────────────────
install:
	pip install -e ".[ingestion,dev]"

test:
	pytest

lint:
	ruff check src tests airflow

# ── Infra (Airflow + MinIO + Postgres) ───────────────────────────
up:
	docker compose up -d

down:
	docker compose down

init:
	docker compose up airflow-init

logs:
	docker compose logs -f airflow-scheduler airflow-webserver

bucket:
	docker compose exec minio mc alias set local http://localhost:9000 $${MINIO_ACCESS_KEY:-minioadmin} $${MINIO_SECRET_KEY:-minioadmin} && \
	docker compose exec minio mc mb --ignore-existing local/$${MINIO_BUCKET_BRONZE:-bronze}

airflow-ui:
	@echo "Airflow: http://localhost:8080  (admin / admin)"

minio-ui:
	@echo "MinIO console: http://localhost:9001"

# ── dbt (fora do container) ──────────────────────────────────────
# Gera sources/models bronze a partir de airflow/configs (costura B)
dbt-generate:
	python -m govhub.sync.dbt_source_generator --configs airflow/configs --models-dir dbt/models

dbt-deps:
	$(DBT) deps $(DBT_ARGS)

dbt-run:
	$(DBT) run $(DBT_ARGS)

dbt-test:
	$(DBT) test $(DBT_ARGS)

.PHONY: install test lint up down init build airflow-lock logs bucket airflow-ui minio-ui dbt-generate dbt-deps dbt-run dbt-test

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

init: build
	docker compose up airflow-init

build:
	docker compose build

# Regenera airflow/requirements.txt a partir de airflow/requirements.in,
# restrito aos pacotes que a imagem base do Airflow já traz (commitar o resultado).
airflow-lock:
	docker run --rm -v "$$PWD/airflow:/work" --entrypoint bash apache/airflow:2.9.2 -c '\
		pip freeze | grep -viE "^(-e|httpx==|httpcore==)" > /tmp/base.txt && \
		PIP_CONSTRAINT= pip install -q "uv>=0.9" && \
		python -m uv pip compile /work/requirements.in -c /tmp/base.txt \
			--override /work/overrides.txt --universal \
			--python-version 3.12 --no-header --no-annotate -q -o /tmp/r.txt && \
		{ echo "# Gerado por \`make airflow-lock\` a partir de requirements.in — não editar à mão."; cat /tmp/r.txt; } > /work/requirements.txt'

logs:
	docker compose logs -f airflow-scheduler airflow-webserver

bucket:
	docker compose exec airflow-scheduler python -c "from govhub.ingestion.storage.bronze import _client, _bucket; c = _client(); b = _bucket(); b in [x['Name'] for x in c.list_buckets()['Buckets']] or c.create_bucket(Bucket=b); print('bucket ok:', b)"

airflow-ui:
	@echo "Airflow: http://localhost:8080  (admin / admin)"

minio-ui:
	@echo "Console S3 (RustFS): http://localhost:9001"

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

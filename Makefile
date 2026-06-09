.PHONY: start up down init logs minio-ui airflow-ui bucket ps test lint

start:
	cp -n .env.example .env || true
	docker compose up -d

up:
	docker compose up -d

down:
	docker compose down -v

init:
	cp -n .env.example .env || true
	docker compose up airflow-init

logs:
	docker compose logs -f airflow-scheduler airflow-webserver

ps:
	docker compose ps

airflow-ui:
	@echo "Airflow: http://localhost:8080  (admin / admin)"

minio-ui:
	@echo "MinIO console: http://localhost:9001  (minioadmin / minioadmin)"

bucket:
	docker compose exec minio mc alias set local http://localhost:9000 $${STORAGE_ACCESS_KEY:-minioadmin} $${STORAGE_SECRET_KEY:-minioadmin} && \
	docker compose exec minio mc mb --ignore-existing local/$${STORAGE_BUCKET_RAW:-raw}

test:
	.venv/bin/python -m pytest core/tests/ -v

lint:
	.venv/bin/python -m ruff check core/ ingestion/

.PHONY: up down init logs minio-ui airflow-ui bucket

up:
	docker compose up -d

down:
	docker compose down

init:
	docker compose up airflow-init

logs:
	docker compose logs -f airflow-scheduler airflow-webserver

airflow-ui:
	@echo "Airflow: http://localhost:8080  (admin / admin)"

minio-ui:
	@echo "MinIO console: http://localhost:9001"

bucket:
	docker compose exec minio mc alias set local http://localhost:9000 $${MINIO_ACCESS_KEY:-minioadmin} $${MINIO_SECRET_KEY:-minioadmin} && \
	docker compose exec minio mc mb --ignore-existing local/$${MINIO_BUCKET_BRONZE:-bronze}

# Ingestion Pipeline

Multi-source DAG ingestion pipeline with config-driven structural and semantic PDF extraction,
bronze/silver medallion zones, feeding the semantic Integration Agent (fase01/src).

## Architecture

| Layer | Tool | Role |
|-------|------|------|
| Orchestration | Apache Airflow 2.x | Schedules and runs all DAGs |
| Source Config | YAML files in `configs/` | Declares extraction rules per source |
| Bronze Zone | MinIO (S3-compatible) | Immutable raw artifact storage |
| Silver Zone | DuckDB (file-based) | Cleaned, queryable staged tables |
| Integration Bridge | `bridge/integration_bridge.py` | Feeds staged tables into IntegrationAgent |

## Components

- **extractors/** — CSV/XLSX, API, DB dump, PDF binary download
- **parsers/** — Structural PDF (pdfplumber + camelot) and Semantic PDF (unstructured + Claude API)
- **storage/** — Bronze (MinIO) and Silver (DuckDB) abstractions
- **bridge/** — Loads table pairs from DuckDB and calls `IntegrationAgent.run()`
- **dags/** — One Airflow DAG per source type + integration trigger DAG
- **configs/** — One YAML per source (controls schedule, extraction mode, columns, pages)

## How to run

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY and adjust MinIO credentials if needed

make init       # initialise Airflow DB and create admin user
make up         # start all services
make bucket     # create bronze bucket in MinIO

make airflow-ui # open http://localhost:8080  (admin / admin)
make minio-ui   # open http://localhost:9001
```

## Adding a new source

1. Create `configs/<source_name>.yaml` following one of the examples in `configs/`
2. The relevant DAG picks it up automatically on next scheduler tick
3. No DAG code changes required

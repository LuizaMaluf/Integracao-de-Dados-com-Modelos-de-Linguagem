# CLAUDE.md

TCC de Luiza Maluf (UnB) — ingestão, transformação e integração semântica de bases governamentais.
Glossário do domínio em `CONTEXT.md`; decisões em `docs/adr/`.

## Estrutura
- `src/govhub/` — pacote Python único: `ingestion/`, `integration/`, `sync/` (costuras A/B), `cli.py`
- `airflow/dags/` (DAGs finas, só orquestram) e `airflow/configs/` (um YAML por fonte)
- `dbt/` — projeto dbt (bronze → silver → gold)
- `tests/{ingestion,integration}/`

## Comandos
- `pip install -e ".[ingestion,dev]"` — instala o pacote
- `make test` / `make lint`
- `make up` — Airflow + MinIO + PostgreSQL (docker-compose na raiz)
- `make dbt-run` — dbt fora do container, lendo o `.env` da raiz
- `govhub --table-a A.csv --table-b B.csv [--no-llm]` — integração via CLI

## Convenções
- Imports sempre absolutos a partir de `govhub.*`; nunca usar `sys.path.insert`.
- Configuração só no `.env` da raiz (modelo em `.env.example`).
- Commits e PRs levam apenas o nome da autora: sem `Co-Authored-By` nem qualquer linha de atribuição a IA/ferramenta.

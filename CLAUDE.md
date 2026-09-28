# CLAUDE.md

TCC de Luiza Maluf (UnB) — ingestão, transformação e integração semântica de bases governamentais.
Glossário do domínio em `CONTEXT.md`; decisões em `docs/adr/`.

## Estrutura
- `src/govhub/` — pacote Python único: `ingestion/` (inclui `registry.py`, contrato do YAML), `integration/`, `sync/` (costuras A/B + e2e), `cli.py`
- `airflow/dags/` (DAGs finas, só orquestram) e `airflow/configs/` (um YAML por fonte)
- `dbt/` — projeto dbt (bronze → silver → gold)
- `tests/{ingestion,integration,sync}/`

## Comandos
- `pip install -e ".[ingestion,dev]"` — instala o pacote
- `make test` / `make lint`
- `make up` — Airflow + MinIO + PostgreSQL (docker-compose na raiz)
- `make dbt-generate` — regenera `dbt/models/bronze/_generated/` a partir de `airflow/configs/` (commitar o resultado)
- `make dbt-run` — dbt fora do container, lendo o `.env` da raiz
- `python -m govhub.sync.e2e <fonte_a> <fonte_b> [--no-llm]` — fluxo costuras A → B → C
- Testes `pg`/`e2e` rodam só com `POSTGRES_*` apontando para um banco acessível
- `govhub --table-a A.csv --table-b B.csv [--no-llm]` — integração via CLI

## Convenções
- Imports sempre absolutos a partir de `govhub.*`; nunca usar `sys.path.insert`.
- Configuração só no `.env` da raiz (modelo em `.env.example`).
- Commits e PRs levam apenas o nome da autora: sem `Co-Authored-By` nem qualquer linha de atribuição a IA/ferramenta.

# CLAUDE.md

TCC de Luiza Maluf (UnB) — ingestão, transformação e integração semântica de bases governamentais.
Glossário do domínio em `CONTEXT.md`; decisões em `docs/adr/`.

## Contexto do TCC
- Orientação: Carla Rocha e Isaque Alves · TCC 1 no início de março de 2027, TCC 2 em agosto de 2027
- Proposta (QPs, metodologia, plano): `docs/tcc/proposta.md`
- Artigo-base (SPAPI-Tester, Wang et al.): `docs/tcc/artigo-base.md` — o TCC replica o método dele em dados públicos
- Princípio de arquitetura (ADR 0011): **LLM embutido** — o LLM só decide o de-para entre bases e devolve um Dicionário de Mapeamento tipado; todo SQL, DAG ou teste executado sai de um estágio determinístico. Nunca pôr o LLM para gerar SQL ou contornar o pipeline.
- Processo (foco da metodologia): **Spec-Driven Development** — mudança não trivial começa por spec em `docs/specs/` (modelo `_template.md`) com critérios de aceite verificáveis; só implementar depois da spec aprovada e preencher o "Registro para a QP5" ao final.
- Avaliação sempre por Categoria de Atrito (`CONTEXT.md`), por modelo e contra baseline sem LLM; ground truth é congelado antes de ajustar o agente.

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

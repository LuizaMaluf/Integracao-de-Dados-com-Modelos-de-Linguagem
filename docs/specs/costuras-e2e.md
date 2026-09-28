# Config-Driven E2E Bridge — Costuras A/B/C

Os três componentes que fecham as costuras de arquitetura identificadas na PoC de
viabilidade (IBGE). **Implementados e testados**, inclusive com PostgreSQL, dbt e
Airflow 2.9.2 reais.

## Objetivo

Estender o princípio config-driven (já vivo na ingestão) às fronteiras entre as três
camadas, de modo que **adicionar uma fonte nova custe apenas um YAML** de ponta a ponta —
ingestão, transformação e integração.

## Componentes

| # | Componente | Costura | Local | ADR |
|---|---|---|---|---|
| 0 | `registry.py` | contrato do YAML | `src/govhub/ingestion/` | 0008 |
| 1 | `silver_sync.py` | A — DuckDB → PostgreSQL | `src/govhub/sync/` | 0009 |
| 2 | `dbt_source_generator.py` | B — dbt config-driven | `src/govhub/sync/` | 0010 |
| 3 | `postgres_loader.py` | C — integração lê do banco | `src/govhub/integration/loaders/` | — |
| — | `e2e.py` | encadeia A → B → C | `src/govhub/sync/` | — |

## Fluxo (um YAML, três camadas)

```
airflow/configs/<fonte>.yaml     (único ponto de configuração)
        │
        ├─► extract → write_bronze → stage_silver        lote <fonte>_YYYYMMDD no DuckDB
        │
        ├─► (A) sync_postgres                            silver.<target_table> no PostgreSQL
        │       + dt_ingest, _silver_table               publica Dataset silver://<target_table>
        │
        ├─► (B) dbt_source_generator                     dbt/models/bronze/_generated/
        │       → dbt run                                bronze.<target_table> (incremental por lote)
        │
        └─► (C) PostgresLoader                           (DataFrame, TableMetadata) → IntegrationAgent
```

## Contrato do YAML

Campos opcionais, todos com padrão (YAMLs antigos continuam válidos):

```yaml
target_table: ibge_municipios            # padrão: source_name normalizado
silver_dataset: silver://ibge_municipios # padrão: silver://<target_table>
dbt_packages:                            # pacotes disparados pelo dataset (DAG factory)
  - name: ibge
    select: models/
```

## Como rodar

```bash
# Costura A: automática — task sync_postgres em toda DAG de ingestão, após stage_silver.

# Costura B: gerar sources/models a partir do registry (commitar o resultado)
make dbt-generate

# Costura C: integração lendo do banco
govhub --table-a pg://silver.ibge_municipios --table-b pg://silver.ibge_estados --no-llm

# Fluxo completo A → B → C para um par do registry (lote mais recente no DuckDB)
python -m govhub.sync.e2e ibge_municipios ibge_estados --no-llm
#   --skip-dbt       pula a costura B e lê de silver.*
#   --dbt-target     target do profiles.yml (padrão: dev → localhost)
```

O JSON de saída (`output/e2e_<a>__<b>.json`) traz, em `e2e`, as linhas sincronizadas e
carregadas e o tempo de cada etapa (`timings_s`) — material para o capítulo de resultados.

## Testes

- Unitários: `tests/sync/`, `tests/ingestion/test_registry.py`,
  `tests/integration/test_postgres_loader.py`.
- Com banco (`@pytest.mark.pg`): rodam quando `POSTGRES_*` aponta para um PostgreSQL
  acessível (ex.: o do `make up`); sem banco, são pulados.
- Fluxo completo (`@pytest.mark.e2e`, `tests/sync/test_e2e.py`): dados no formato da API
  do IBGE → Silver Sync → dbt → integração. Precisa também do `dbt` e de `make dbt-deps`.
- `test_models_gerados_no_repo_estao_atualizados` falha se `airflow/configs` mudar sem
  `make dbt-generate`.

## Decisões de design (rastreabilidade)

- **Costura A — ponte automática** (não Postgres como silver único): preserva o DuckDB
  na ingestão; carga idempotente por lote. (ADR 0009)
- **Costura B — gerador próprio lendo o Source Registry** (não `dbt-codegen` oficial):
  gerar a partir do YAML é o que sustenta a tese de portabilidade por configuração.
  Contribuição original do TCC. (ADR 0010)
- **Costura C — `PostgresLoader(BaseLoader)`**: simétrico ao `CsvLoader`; remove as
  colunas de linhagem para não virarem falsas candidatas a chave.

## Limitações conhecidas

- Colunas aninhadas chegam ao Postgres como texto JSON (não `JSONB`).
- Colunas novas da fonte entram como `TEXT`; tipar é papel do silver no dbt.
- A DAG factory (`transformation_dag_factory.py`) roda pacotes em `dbt/dbt_packages/<pacote>`;
  os models gerados vivem no projeto principal e rodam pelo `transformation_dag` diário
  ou pelo `e2e`.
- Resultado da PoC IBGE sem LLM: a Decision Layer escolhe `nome ↔ nome`; a chave correta
  (código da UF como prefixo do código do município, ou o `id` aninhado em
  `microrregiao.mesorregiao.UF`) exige a etapa com LLM ou detecção de Derived Key em JSON.

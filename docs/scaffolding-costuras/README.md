# Config-Driven E2E Bridge — Scaffolding das Costuras A/B/C

Esqueletos dos três componentes que fecham as costuras de arquitetura identificadas na
PoC de viabilidade (ver `docs/pocs/01-viabilidade-e2e/`). São **stubs** — a estrutura,
as assinaturas e as responsabilidades estão definidas, mas a lógica de negócio ainda
não está preenchida. Revise e mova cada arquivo para o diretório real da sua camada
quando for implementar.

## Objetivo

Estender o princípio config-driven (já vivo na ingestão) às fronteiras entre as três
camadas, de modo que **adicionar uma fonte nova custe apenas um YAML** de ponta a ponta —
ingestão, transformação e integração.

## Componentes

| # | Componente | Costura | Destino real sugerido |
|---|---|---|---|
| 1 | `silver_sync.py` | A — DuckDB → PostgreSQL | `ingestion/storage/` |
| 2 | `dbt_source_generator.py` | B — dbt config-driven | `ingestion/dags/` ou `transformation/` |
| 3 | `postgres_loader.py` | C — integração lê do banco | `integration/src/loaders/` |

## Fluxo (um YAML, três camadas)

```
ingestion/configs/<fonte>.yaml   (único ponto de configuração)
        │
        ├─► [já existe] extract → write_bronze → stage_silver (DuckDB)
        │
        ├─► (1) Silver Sync      DuckDB → silver.<fonte> no PostgreSQL
        │
        ├─► (2) Source Generator lê o YAML → gera sources.yml + model bronze → dbt run
        │
        └─► (3) Postgres Loader  lê silver.<fonte> do PG → (DataFrame, TableMetadata) → IntegrationAgent
```

## Decisões de design (rastreabilidade)

- **Costura A — ponte automática** (não Postgres como silver único): preserva o DuckDB
  na ingestão; a sincronização roda como task do Airflow. (escolha do usuário)
- **Costura B — gerador próprio lendo o Source Registry** (não `dbt-codegen` oficial):
  o `dbt-codegen` gera por introspecção do banco; gerar a partir do YAML é o que sustenta
  a tese de portabilidade por configuração. Contribuição original do TCC. (ver ADR 0010)
- **Costura C — `PostgresLoader(BaseLoader)`**: simétrico ao `CsvLoader` existente,
  não-invasivo na camada de integração.

## Como rodar (após implementar e mover para os diretórios reais)

```bash
# 1. Silver Sync roda automaticamente como task do api_dag após stage_silver
# 2. Gerar artefatos dbt a partir dos YAMLs:
python -m ingestion.dags.dbt_source_generator --configs ingestion/configs --out transformation/models/bronze
# 3. Integração lê do banco:
python integration/main.py --table-a pg://silver.ibge_municipios --table-b pg://silver.ibge_estados
```

## Dependências

Ver `requirements.txt` nesta pasta — todas já presentes no projeto, exceto onde anotado.

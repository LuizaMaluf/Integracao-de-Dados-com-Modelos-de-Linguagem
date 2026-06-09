# Integração de Dados com Modelos de Linguagem — CLAUDE.md

Pipeline config-driven de ingestão, transformação e integração semântica de bases governamentais.
Desenvolvido como TCC de Lucas Bottino e Luiza Maluf (UnB / Lab Livre).

A branch `poc-arquitetura-govhub` integra o **Provider Abstraction Pattern** da PoC, que permite servir múltiplos clientes com infraestruturas diferentes (MinIO/S3, PostgreSQL/BigQuery) sem fork de código.

---

## Arquitetura

```
Fontes (API REST, CSV/XLSX, SQL dump, PDF)
    │
    │  Airflow DAGs — config-driven via YAML
    ▼
MinIO (object storage)          ← RAW / Bronze: Parquet imutável
    │
    │  DuckDB adapter
    ▼
PostgreSQL (DW)                 ← Bronze → Silver (staging)
    │
    │  dbt (gov_hub project)
    ▼
Bronze → Silver → Gold          ← transformações, métricas
    │
    │  Integration Bridge DAG
    ▼
DuckDB (análise semântica)      ← profiling, evidence layer
    │
    │  Claude API (LLM)
    ▼
Integration Report (HTML)       ← chaves de integração, confiança
```

### Camadas de dados

| Camada | Tecnologia | Descrição |
|--------|-----------|-----------|
| **Raw/Bronze** | MinIO + PostgreSQL | Parquet imutável + tabela de staging |
| **Silver** | PostgreSQL + dbt | Limpeza, tipagem, enriquecimento |
| **Gold** | PostgreSQL + dbt | Agregações e métricas para consumo |
| **Integração** | DuckDB + Claude API | Matching semântico de chaves entre bases |

---

## Provider Abstraction Pattern (branch `poc-arquitetura-govhub`)

`CLIENT_NAME` (env var) seleciona `clients/<nome>.yaml`, que declara qual provider usar para storage e warehouse. O código nunca referencia MinIO ou PostgreSQL diretamente — só as interfaces abstratas `StorageProvider` e `WarehouseProvider`.

```
clients/
└── poc.yaml   ← MinIO + PostgreSQL (dev local)
```

Factory em `ingestion/providers/__init__.py`: `get_storage()` e `get_warehouse()`.

---

## Estrutura de diretórios

```
Integracao-de-Dados-com-Modelos-de-Linguagem/
├── clients/                     # Config de infra por cliente (Provider Pattern)
│   └── poc.yaml
├── ingestion/
│   ├── configs/                 # Source Registry — um YAML por fonte
│   │   ├── example_api.yaml
│   │   ├── example_csv.yaml
│   │   ├── example_dump.yaml
│   │   └── example_pdf_*.yaml
│   ├── dags/
│   │   ├── api_dag.py           # DAG factory: type=api
│   │   ├── csv_xlsx_dag.py      # DAG factory: type=csv_xlsx
│   │   ├── dump_dag.py          # DAG factory: type=dump
│   │   ├── pdf_structural_dag.py
│   │   ├── pdf_semantic_dag.py
│   │   ├── integration_bridge_dag.py
│   │   └── transformation_dag.py
│   ├── extractors/
│   │   ├── api_extractor.py     # REST genérico (auth, paginação)
│   │   └── ...
│   ├── parsers/                 # PDF parsers (structural + semantic via Claude)
│   ├── storage/                 # bronze.py, silver.py (camada de persistência)
│   └── providers/               # Provider Abstraction (PoC) — em integração
│       ├── __init__.py          # get_storage(), get_warehouse()
│       ├── storage/             # StorageProvider ABC + MinIO + S3
│       └── warehouse/           # WarehouseProvider ABC + Postgres + BigQuery stub
├── transformation/              # dbt project "gov_hub"
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── bronze/              # incremental, unique_key
│       ├── silver/              # table, limpeza + enriquecimento
│       └── gold/                # table, agregações
├── integration/                 # Pipeline LLM de integração semântica
│   ├── main.py
│   └── src/
│       ├── agent/               # orchestrator, candidate_generator, llm_reasoner
│       ├── analyzers/           # structural, semantic, statistical, content
│       ├── transformers/        # pattern_detector, normalizer
│       └── config/              # context_loader, settings
├── .claude/
│   └── skills/
│       ├── analisar-tabela/     # Perfila colunas de um CSV
│       ├── comparar-colunas/    # Evidence Layer (pares candidatos)
│       ├── identificar-chave/   # Decision Layer (LLM raciocina sobre evidências)
│       ├── integrar-bases/      # Pipeline completo de 5 etapas
│       ├── mapear-integracoes/  # Batch discovery de joins
│       ├── gerar-relatorio/     # HTML report a partir de JSON
│       ├── definir-contexto/    # Domain Context generator
│       ├── criar-dag/           # Gera YAML de config para nova fonte
│       └── criar-dbt/           # Gera modelo dbt bronze/silver/gold
├── artefatos/                   # ADRs, PRDs, docs arquiteturais
├── CONTEXT.md                   # Glossário do domínio de dados governamentais
└── docker-compose.yml
```

---

## Anatomia de um config YAML (`ingestion/configs/`)

### type: api

```yaml
source_name: siafi_empenhos      # nome único — vira schema no DW e prefixo do dag_id
type: api
schedule: "@daily"

url: "https://api.portaldatransparencia.gov.br/api-de-dados/despesas/por-orgao"

auth_strategy: api_key_header    # none | bearer | api_key_header
auth_header: chave-api
auth_env_var: SIAFI_API_KEY      # nome da env var com o token

pagination_strategy: page_number # none | cursor | page_number | offset
page_param: pagina
page_size: 500
page_size_param: quantidade

params:                          # query params estáticos
  ano: 2024
  orgao: "26000"

records_path: data               # caminho pontilhado para lista de registros no JSON
has_more_field: hasNext          # campo booleano de controle de paginação
```

### type: csv_xlsx

```yaml
source_name: fgv_igp
type: csv_xlsx
schedule: "@monthly"

file_path: /opt/airflow/data/fgv_igp.csv
separator: ";"
encoding: utf-8
```

### type: dump

```yaml
source_name: siape_servidores
type: dump
schedule: "@monthly"

connection_env: SIAPE_CONN
query: "SELECT * FROM servidores WHERE ativo = 1"
```

**Regras:**
- `source_name` vira schema no DW e prefixo do `dag_id`
- Cada `type` tem seu próprio DAG factory em `ingestion/dags/`
- `auth_strategy: bearer` exige `auth_env_var` com o nome da env var do token
- `records_path` usa dot-notation (ex: `data.items.records`)

---

## Anatomia de um modelo dbt (`transformation/models/`)

### Bronze — incremental, fonte de staging

```sql
{{ config(
    materialized='incremental',
    unique_key='<chave_primaria>',
    on_schema_change='sync_all_columns'
) }}

select *
from {{ source('silver', '<tabela_staging>') }}

{% if is_incremental() %}
  where dt_ingest > (select max(dt_ingest) from {{ this }})
{% endif %}
```

### Silver — table, limpeza e enriquecimento

```sql
{{ config(materialized='table') }}

select
    <colunas_tipadas_e_renomeadas>
from {{ ref('<modelo_bronze>') }}
where <filtros_de_qualidade>
```

### Gold — table, agregações para consumo

```sql
{{ config(materialized='table') }}

select
    <dimensoes>,
    sum(<valor>) as <metrica>
from {{ ref('<modelo_silver>') }}
group by <dimensoes>
```

**Convenções dbt:**
- Projeto: `gov_hub` (dbt_project.yml)
- Schemas: `bronze`, `silver`, `gold`
- Bronze: sempre `incremental` com `unique_key`
- Silver/Gold: sempre `table`
- Joins entre modelos: use `{{ ref(...) }}` para modelos e `{{ source(...) }}` para staging

---

## Pipeline de Integração Semântica (LLM)

5 etapas orquestradas pela skill `/integrar-bases`:

| Etapa | O que faz |
|-------|-----------|
| 0. Validar contexto | Verifica cobertura do Domain Context (≥ 60%) |
| 1. Analisar tabelas | Perfil de colunas (dtype, cardinalidade, nulos, top-5) |
| 2. Comparar colunas | Evidence Layer: pares candidatos a join key |
| 3. Identificar chave | Decision Layer: Claude API raciocina sobre as evidências |
| 4. Gerar relatório | HTML com confiança, código Python/SQL sugerido |

---

## Skills disponíveis

| Skill | Dispara quando |
|-------|----------------|
| `/criar-dag` | Precisa adicionar nova fonte de dados ao pipeline |
| `/criar-dbt` | Precisa criar modelo bronze, silver ou gold |
| `/integrar-bases` | Quer o pipeline completo de integração de duas tabelas |
| `/mapear-integracoes` | Quer descobrir joins em batch num diretório |
| `/analisar-tabela` | Quer perfilar colunas de um CSV |
| `/comparar-colunas` | Quer gerar Evidence Layer manualmente |
| `/identificar-chave` | Quer só o Decision Layer (já tem evidências) |
| `/gerar-relatorio` | Quer gerar HTML a partir de JSON de resultado |
| `/definir-contexto` | Quer criar um Domain Context para um domínio novo |

---

## Stack

- **Apache Airflow 2.9** — orquestração
- **MinIO** — object storage S3-compatible (raw/bronze zone)
- **PostgreSQL** — data warehouse (bronze/silver/gold)
- **DuckDB** — motor ETL e análise semântica
- **dbt** (`gov_hub`) — transformações SQL
- **Claude API** (Anthropic) — raciocínio semântico na integração de bases
- Python: `httpx`, `pandas`, `pyarrow`, `boto3`, `duckdb`, `sqlalchemy`, `PyYAML`, `anthropic`

---

## Comandos

```bash
# Ingestion stack
make up          # sobe Airflow + MinIO + PostgreSQL
make down        # para e remove volumes
make logs        # tail nos logs do scheduler

# dbt (dentro do container ou com profile configurado)
dbt run          # executa todos os modelos
dbt run --select silver.*   # só modelos silver
dbt test         # roda testes de qualidade

# Integration pipeline
cd integration && python main.py <tabela_a> <tabela_b>
```

---

## Decisões arquiteturais

- **ADR 0002** — DAG Factory config-driven (elimina DAGs individuais por fonte)
- **ADR 0003** — Bronze Store com object storage (imutabilidade, replay)
- **ADR 0004** — Provider Abstraction Pattern (multi-cliente sem fork)
- **CONTEXT.md** — Glossário do domínio orçamentário federal (usado pelo LLM)

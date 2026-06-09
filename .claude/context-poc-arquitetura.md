# Contexto de sessão — integração da PoC de Arquitetura

Este documento resume uma sessão de trabalho feita no repositório `poc-arquitetura-govhub` e o que foi trazido para este repositório (`Integracao-de-Dados-com-Modelos-de-Linguagem`) na branch `poc-arquitetura-govhub`.

---

## Os três repositórios

| Repositório | Caminho | Papel |
|-------------|---------|-------|
| **PoC Arquitetura** | `~/Workspace/lablivre/pocs/poc-arquitetura-govhub` | PoC com Provider Abstraction Pattern. Fonte de verdade dos providers e do padrão de config YAML |
| **TCC (este repo)** | `~/Workspace/unb/tcc/Integracao-de-Dados-com-Modelos-de-Linguagem` | Pipeline completo: ingestão + transformação + integração semântica com LLM. Branch `poc-arquitetura-govhub` incorpora a arquitetura da PoC |
| **GovHub produção** | `~/Workspace/lablivre/data-application-cidades` | Alvo final da refatoração. 17+ conectores, ainda sem Provider Abstraction |

---

## O que foi feito nesta sessão

Todos os arquivos abaixo estão **não commitados** na branch `poc-arquitetura-govhub` deste repositório.

### Arquivos criados

| Arquivo | O que é |
|---------|---------|
| `CLAUDE.md` | Documentação da arquitetura completa para o Claude Code |
| `docker-compose.yml` | Unificado na raiz: Provider Abstraction + ANTHROPIC_API_KEY + data-db (PostgreSQL DW) |
| `.env.example` | Unificado: infra (MinIO, Postgres, Airflow) + pipeline semântico (limiares, modelo) |
| `Makefile` | Movido de `ingestion/` para a raiz; `init` copia `.env.example`, `bucket` usa `MINIO_BUCKET_RAW` |
| `clients/poc.yaml` | Config do Provider Abstraction: MinIO + PostgreSQL |
| `ingestion/providers/__init__.py` | Factory: `get_storage()` e `get_warehouse()` |
| `ingestion/providers/storage/base.py` | ABC `StorageProvider` |
| `ingestion/providers/storage/minio.py` | Implementação MinIO |
| `ingestion/providers/storage/s3.py` | Implementação AWS S3 |
| `ingestion/providers/warehouse/base.py` | ABC `WarehouseProvider` |
| `ingestion/providers/warehouse/postgres.py` | DuckDB → PostgreSQL (normaliza snake_case, adiciona `_loaded_at`) |
| `ingestion/providers/warehouse/bigquery.py` | Stub BigQuery |
| `.claude/skills/criar-dag/SKILL.md` | Skill que gera YAML de config para nova fonte de dados |
| `.claude/skills/criar-dbt/SKILL.md` | Skill que gera modelo dbt bronze/silver/gold |

### Arquivos removidos

| Arquivo removido | Por quê |
|-----------------|---------|
| `ingestion/docker-compose.yml` | Movido e unificado na raiz do projeto |
| `ingestion/.env` | Movido e unificado na raiz (não esqueça de copiar a `ANTHROPIC_API_KEY` real para o novo `.env`) |
| `ingestion/.env.example` | Idem |
| `ingestion/Makefile` | Movido para a raiz |

---

## Provider Abstraction Pattern

O padrão central que a PoC introduz: `CLIENT_NAME` (env var) seleciona `clients/<nome>.yaml`, que declara qual provider usar. O código Python nunca referencia MinIO ou PostgreSQL diretamente.

```
CLIENT_NAME=poc  →  clients/poc.yaml  →  MinIOProvider + PostgreSQLProvider
```

Factory em `ingestion/providers/__init__.py`:
```python
from providers import get_storage, get_warehouse

storage = get_storage()   # retorna MinIOProvider (ou S3Provider, GCSProvider...)
wh = get_warehouse()      # retorna PostgreSQLProvider (ou BigQueryProvider...)
```

Os DAGs existentes neste repo ainda usam `ingestion/storage/bronze.py` e `ingestion/storage/silver.py` diretamente (módulo legado). A migração para `providers/` é gradual — novos DAGs devem usar `get_storage()` e `get_warehouse()`.

---

## Estrutura atual do projeto (nesta branch)

```
Integracao-de-Dados-com-Modelos-de-Linguagem/
├── clients/
│   └── poc.yaml                  ← MinIO + PostgreSQL
├── ingestion/
│   ├── configs/                  ← YAMLs de config das fontes
│   ├── dags/                     ← api_dag.py, csv_xlsx_dag.py, dump_dag.py, pdf_*_dag.py
│   ├── extractors/               ← api_extractor.py e outros
│   ├── parsers/                  ← PDF structural + semantic (Claude API)
│   ├── storage/                  ← bronze.py, silver.py (legado — ainda em uso)
│   ├── bridge/
│   └── providers/                ← NOVO: Provider Abstraction Pattern
│       ├── __init__.py           ← get_storage(), get_warehouse()
│       ├── storage/              ← base.py, minio.py, s3.py
│       └── warehouse/            ← base.py, postgres.py, bigquery.py
├── transformation/               ← dbt project "gov_hub" (bronze/silver/gold)
├── integration/                  ← Pipeline LLM: agent/, analyzers/, transformers/
├── .claude/
│   └── skills/                   ← 10 skills: 8 originais + criar-dag + criar-dbt
├── CLAUDE.md                     ← documentação da arquitetura
├── CONTEXT.md                    ← glossário do domínio orçamentário federal
├── docker-compose.yml            ← stack completa na raiz
├── .env.example                  ← template de variáveis
└── Makefile                      ← up / down / init / logs / ps / bucket
```

---

## Skills disponíveis (`.claude/skills/`)

| Skill | Descrição |
|-------|-----------|
| `/criar-dag` | Gera YAML de config em `ingestion/configs/` para nova fonte (api, csv_xlsx, dump) |
| `/criar-dbt` | Gera modelo dbt `.sql` em `transformation/models/bronze|silver|gold/` |
| `/integrar-bases` | Pipeline completo de integração semântica entre duas tabelas |
| `/mapear-integracoes` | Batch discovery de joins em um diretório |
| `/analisar-tabela` | Perfil de colunas de um CSV |
| `/comparar-colunas` | Evidence Layer manual |
| `/identificar-chave` | Decision Layer (LLM sobre evidências) |
| `/gerar-relatorio` | HTML de integração a partir de JSON |
| `/definir-contexto` | Domain Context generator |

---

## Anatomia dos configs YAML (`ingestion/configs/`)

### type: api
```yaml
source_name: siafi_empenhos
type: api
schedule: "@daily"
url: "https://api.portaldatransparencia.gov.br/api-de-dados/..."
auth_strategy: api_key_header   # none | bearer | api_key_header
auth_header: chave-api
auth_env_var: SIAFI_API_KEY
pagination_strategy: page_number
page_param: pagina
page_size: 500
page_size_param: quantidade
records_path: data
has_more_field: hasNext
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

---

## dbt project: `gov_hub`

| Camada | Materialização | Padrão |
|--------|---------------|--------|
| bronze | incremental | `unique_key`, filtro por `dt_ingest` |
| silver | table | limpeza, tipagem, joins |
| gold | table | agregações, métricas |

---

## Convenções importantes

- `source_name` vira schema no DW e prefixo do `dag_id`
- Colunas no warehouse: sempre snake_case (normalizado via DuckDB no `PostgreSQLProvider`)
- `_loaded_at` é adicionado automaticamente pelo `PostgreSQLProvider.load()`
- Providers novos: herdar `StorageProvider` ou `WarehouseProvider` e registrar em `providers/__init__.py`
- DAGs novos: usar `get_storage()` e `get_warehouse()` (não importar MinIO/Postgres diretamente)
- `ANTHROPIC_API_KEY` deve ser setada no `.env` local (não comitar)

---

## Próximos passos sugeridos

1. **Commitar** o que está em staging: `git add -A && git commit -m "feat: integra PoC de arquitetura (providers, docker-compose, skills, CLAUDE.md)"`
2. **Copiar a `ANTHROPIC_API_KEY`** do antigo `ingestion/.env` para o novo `.env` na raiz
3. **Testar a stack**: `make init && make up`
4. **Migrar DAGs existentes** para usar `get_storage()` / `get_warehouse()` ao invés de `storage/bronze.py`
5. **Criar configs YAML** para as fontes reais com `/criar-dag`

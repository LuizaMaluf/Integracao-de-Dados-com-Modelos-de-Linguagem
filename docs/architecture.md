# Arquitetura — Config-Driven Medallion Ingestion com Integration Gateway

## Visão geral

O pipeline recebe dados de fontes governamentais heterogêneas (APIs REST, dumps SQL, PDFs), preserva os artefatos brutos em objeto de armazenamento imutável, normaliza e valida antes de persistir no banco analítico, e expõe as tabelas carregadas para identificação automática de chaves de integração entre bases.

A refatoração substitui 73 arquivos de DAG hard-coded e 15+ clientes HTTP por um pipeline config-driven: cada fonte governamental é declarada em um YAML; um DAG Factory gera os DAGs automaticamente; um Generic Extractor substitui os clientes por fonte.

---

## Camadas

```
Source Registry (YAML por fonte)
        │
        ▼
DAG Factory ──── gera DAGs para todas as fontes do registro
        │
        ▼
Generic Extractor ──── API → IO.Bytes (paginação, retry, auth by config)
        │
        ▼
Bronze Store (MinIO) ──── raw/<source>/<date>/response.json
        │
        ▼
Transform + Validate ──── parse + normalize + schema check
        │
        ▼
Silver Store (PostgreSQL) ──── schema.<source>/<tabela>
        │
        ▼
Table Catalog ──── catalog.ingested_tables
        │
        ├──── DBT + Superset (Gold Layer)
        │
        ▼
Integration Gateway ──── par de tabelas → IntegrationAgent
        │                                        │
        │                                        ▼
        │                              Context Store (schema context)
        │                              ┌─ domain_contexts
        │                              ├─ column_annotations  ◀── annotate_context task
        │                              ├─ table_profiles      ◀── profile_table task
        │                              └─ integration_discoveries ◀── bridge.py
        │                                        │
        │                                 ContextResolver
        │                                        │
        ▼                                        ▼
output/identificar_chave_<a>__<b>.json   DbtTaskGroup (--select dinâmico)
```

---

## Componentes

### 1. Source Registry

**Responsabilidade:** declaração centralizada e versionada de todas as fontes de dados.

**Ferramenta:** arquivos YAML validados por Pydantic.

**Por quê:** adicionar uma fonte nova requer apenas criar um YAML — sem código Python novo. Toda a configuração (URL, auth, paginação, schedule, schema alvo) fica no repositório, revisável via PR.

**Estrutura de um registro de fonte:**
```yaml
source_name: siafi_notas_empenho
type: api
schedule: "@daily"
url: "https://api.portaldatransparencia.gov.br/api-de-dados/..."
auth_strategy: api_key_header
auth_header: chave-api
auth_env_var: SIAFI_API_KEY
pagination_strategy: page_number
page_param: pagina
page_size: 500
records_path: data
has_more_field: hasNext
target_schema: siafi
target_table: notas_empenho
conflict_fields: [numEmpenho, anoEmpenho]
```

---

### 2. DAG Factory

**Responsabilidade:** lê o Source Registry e gera todos os DAGs do Airflow dinamicamente, sem arquivos de DAG individuais.

**Ferramenta:** `astronomer/dag-factory`.

**Por quê:** elimina os 73 arquivos de DAG existentes. Um único `dag_factory.yaml` os substitui. Alterar schedule ou adicionar retry não requer editar código Python.

---

### 3. Generic Extractor

**Responsabilidade:** realiza a extração HTTP de qualquer fonte declarada no Source Registry — paginação (cursor, page_number, offset), retry com backoff exponencial, autenticação (bearer, api_key_header, none), streaming do resultado para buffer em memória.

**Ferramenta:** `httpx` + extensão da `ClienteBase` existente.

**Por quê:** substitui os 15+ `ClienteXXX` com lógica duplicada. A `ClienteBase` já implementa retry e HTTP; o Generic Extractor parametriza o comportamento de paginação e auth via config, sem subclasse por fonte.

**Famílias de API cobertas:** array cru no top-level (`records_path` vazio, ex.: IBGE) e objeto OData com wrapper (`records_path: value`, ex.: BCB Olinda) — ambas validadas com dado real na PoC E2E. Há também a estratégia `offset`/`limit` (PostgREST), implementada no extractor e validada por teste com mock. A primeira fonte de uma família nova custou ~14 linhas na classe genérica — não por fonte. Ver `docs/pocs/01-viabilidade-e2e/poc-viabilidade-e2e.md`.

---

### 4. Bronze Store

**Responsabilidade:** armazena o artefato bruto imutável de cada ingestão. Uma escrita por execução, nunca sobrescrita.

**Ferramenta:** MinIO (S3-compatible, self-hosted).

**Convenção de path:** `raw/<source_name>/<YYYY-MM-DD>/response.json`

**Por quê:** o pipeline atual vai direto de API para PostgreSQL — se precisar reprocessar (mudança de schema, bug no parser, auditoria), é necessário re-bater na API. O Bronze Store elimina esse problema: o dado bruto está sempre disponível para reprocessamento sem nova requisição.

---

### 5. Transform + Validate

**Responsabilidade:** deserializa o artefato bronze, normaliza nomes de coluna, valida o schema declarado no YAML da fonte, descarta ou sinaliza registros inválidos antes de escrever no silver.

**Ferramenta:** `pandas` + `pandera`.

**Por quê:** o pipeline atual não tem gate de qualidade entre a API e o PostgreSQL. Pandera permite declarar o schema esperado (tipos, nulos, ranges) junto da definição da fonte, no YAML. Problemas de qualidade falham a task do Airflow antes de sujar o silver.

---

### 6. Silver Store

**Responsabilidade:** tabelas estruturadas por schema de origem, acessíveis por múltiplos processos concorrentes.

**Ferramenta:** PostgreSQL (já existente no projeto).

**Organização:** um schema PostgreSQL por sistema de origem (`siafi`, `compras_gov`, `siape`, `siconv`, etc.).

**Sem mudança em relação ao estado atual** — o Silver Store mantém a mesma estrutura de schemas.

---

### 7. Schema Registry

**Responsabilidade:** versionamento e migration do schema do silver. Os models dbt são o contrato de schema — nenhum schema é criado diretamente em runtime pelo código de ingestão.

**Ferramenta:** `dbt` (já existente no projeto).

**Por quê:** o `create_table_if_not_exists` em runtime no `ClientPostgresDB` cria drift silencioso de schema sem histórico. Com dbt como Schema Registry, toda mudança de schema passa por um model dbt revisável.

---

### 8. Table Catalog

**Responsabilidade:** registra cada carga bem-sucedida no silver com metadados de rastreabilidade.

**Ferramenta:** tabela PostgreSQL no schema `catalog`.

**Schema da tabela `catalog.ingested_tables`:**
```sql
CREATE TABLE catalog.ingested_tables (
    id          SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    table_name  TEXT NOT NULL,
    schema_name TEXT NOT NULL,
    row_count   INTEGER,
    quality_ok  BOOLEAN,
    loaded_at   TIMESTAMPTZ DEFAULT now()
);
```

**Por quê:** sem o Catalog, o Integration Gateway não tem como saber quais tabelas estão disponíveis sem varredura do banco. O Catalog torna a descoberta consultável e auditável.

---

### 9. Integration Gateway

**Responsabilidade:** consulta o Table Catalog para encontrar pares de tabelas carregadas, aciona o IntegrationAgent para identificação de chaves de integração, persiste o resultado.

**Ferramenta:** `bridge/integration_bridge.py` (implementado em `tcc/gov-hub/integration/`).

**Por quê:** desacopla a camada de ingestão da lógica de mapeamento de chaves. O gateway é acionado via DAG separada (`integration_bridge_dag`) com `table_a` e `table_b` como parâmetros, ou via consulta ao Catalog para descoberta automática de pares.

**Output:** `output/identificar_chave_<table_a>__<table_b>.json`

---

### 10. Gold Layer

**Responsabilidade:** modelos analíticos sobre o silver, prontos para consumo pelo Superset.

**Ferramenta:** `dbt` + Apache Superset (já existentes no projeto).

**Sem mudança em relação ao estado atual.**

---

### 11. Context Store

**Responsabilidade:** acumular conhecimento de domínio e integrações ao longo das execuções do pipeline — grupos semânticos, anotações de colunas, perfis de tabelas e chaves de integração descobertas com evidências LLM.

**Ferramenta:** schema `context` no PostgreSQL, gerenciado pelo dbt como Schema Registry.

**Quatro tabelas:**

| Tabela | Escrito por | Lido por |
|---|---|---|
| `context.domain_contexts` | CLI `/definir-contexto` | `find_domain_group`, `/mapear-integracoes` |
| `context.column_annotations` | task `annotate_context` (pós `stage_silver`) | `mapear-integracoes`, `ContextResolver` |
| `context.table_profiles` | task `profile_table` (paralela à `annotate_context`) | `mapear-integracoes` |
| `context.integration_discoveries` | `bridge.py` (pós `IntegrationAgent`) | `ContextResolver` → `DbtTaskGroup` |

**`ContextResolver`:** componente Python entre o Context Store e o cosmos. Antes do `DbtTaskGroup`, consulta `integration_discoveries` com `min_confidence=0.7` e retorna `--select models/` (pipeline completo) quando há integração confirmada, ou `--select models/bronze/` (só bronze) quando não há.

**DAG de ingestão revisado:**
```
extract → write_bronze → stage_silver → annotate_context  (leve)
                                    ↘ profile_table        (pesado, paralelo)
```

**Por quê:** sem o Context Store, cada run recalcula tudo do zero. Grupos de domínio ficam hardcoded em Python e novos domínios exigem deploy. O dbt não sabe quais modelos executar sem um mediador que consulte as integrações confirmadas.

---

## Fluxo de dados — exemplo concreto

**Cenário:** nova nota de empenho do SIAFI disponível na API do Portal da Transparência.

1. **DAG Factory** gerou o DAG `siafi_notas_empenho_ingest` a partir do Source Registry.
2. O Airflow executa o DAG no schedule `@daily`.
3. **Generic Extractor** pagina a API (`pagina=1, 2, ...`) até `hasNext = false`. Resultado: 8.400 registros em `IO.BytesIO`.
4. **Bronze Store** serializa o buffer como JSON e escreve em MinIO: `raw/siafi_notas_empenho/2026-06-07/response.json`. Uma escrita, imutável.
5. **Transform + Validate** lê o JSON do MinIO, normaliza colunas (`numEmpenho` → `num_empenho`), valida schema Pandera. 3 registros com `anoEmpenho` nulo são descartados — warning logado.
6. **Silver Store** recebe 8.397 linhas e insere em `siafi.notas_empenho` via upsert (`ON CONFLICT (num_empenho, ano_empenho)`).
7. **Table Catalog** registra: `source=siafi_notas_empenho`, `table=notas_empenho`, `schema=siafi`, `row_count=8397`, `quality_ok=true`, `loaded_at=2026-06-07T14:31:05Z`.
8. Operador ou DAG automatizada consulta o Catalog, encontra `siafi.notas_empenho` e `transfere_gov.planos_acao` como par candidato.
9. **Integration Gateway** carrega os dois DataFrames do PostgreSQL e chama o IntegrationAgent.
10. **IntegrationAgent** identifica `num_empenho ↔ nr_empenho` como Integration Key. Resultado em `output/identificar_chave_notas_empenho__planos_acao.json`.

---

### 12. Transformation DAG Factory

**Responsabilidade:** lê os Source Registry YAMLs, extrai as declarações `dbt_packages` de cada fonte e gera um DAG de transformação `transform_<pkg>` por pacote dbt — com data-aware scheduling e `--select` dinâmico.

**Ferramenta:** `ingestion/dags/transformation_dag_factory.py` + Airflow Datasets + ContextResolver.

**Por quê:** o `transformation_dag.py` manual executava todos os modelos dbt em cron fixo, sem discriminar pacote ou estado de integração. A factory elimina esse problema em dois eixos: (1) data-aware scheduling — o DAG `transform_<pkg>` só dispara quando o Dataset correspondente do silver é produzido, sem runs em vazio; (2) `--select` dinâmico via ContextResolver — roda só `models/bronze/` enquanto não há integração confirmada, e `models/` (pipeline completo) quando há discovery com confiança ≥ 0.7.

**Relação com o DAG Factory de ingestão (Componente 2):** são factories distintas. A de ingestão gera DAGs `ingest_<source>` a partir de `dag_factory.yaml`. A de transformação gera DAGs `transform_<pkg>` a partir do campo `dbt_packages` nos YAMLs das fontes. Ambas seguem o mesmo princípio config-driven: adicionar uma fonte ou pacote novo não requer código Python.

---

## Decisões de design — referência rápida

| Decisão | ADR |
|---|---|
| Substituir DAGs individuais por DAG Factory config-driven | [ADR 0002](adr/0002-dag-factory-config-driven.md) |
| Adicionar Bronze Store (MinIO) antes do Silver | [ADR 0003](adr/0003-bronze-store-minio.md) |
| Integration Gateway como ponte entre ingestion e IntegrationAgent | [ADR 0004](adr/0004-integration-gateway.md) |
| Context Store passivo — quatro tabelas no schema `context` | [ADR 0005](adr/0005-context-store-passivo.md) |
| Profile em dois momentos + `ContextResolver` como mediador dbt | [ADR 0006](adr/0006-profile-dois-momentos-context-resolver.md) |
| Invalidação diferenciada + `find_domain_group` conectado ao banco | [ADR 0007](adr/0007-invalidacao-diferenciada-find-domain-group.md) |
| Transformation DAG Factory config-driven com data-aware scheduling | [ADR 0008](adr/0008-transformation-dag-factory-data-aware.md) |
| Backend de inferência LLM selecionável (API ou CLI de subscrição) | [ADR 0009](adr/0009-llm-backend-selecionavel.md) |
| Estender o princípio config-driven à camada de transformação (proposto) | [ADR 0010](adr/0010-config-driven-na-transformacao.md) |

---

## Estrutura de diretórios proposta

```
data-application-gov-hub/
├── airflow_lappis/
│   ├── configs/                    ← Source Registry (um YAML por fonte)
│   │   ├── siafi_notas_empenho.yaml
│   │   ├── siafi_nota_credito.yaml
│   │   ├── compras_gov_contratos.yaml
│   │   └── ...
│   ├── dag_factory.yaml            ← geração dinâmica de todos os DAGs
│   ├── dags/
│   │   ├── dag_factory_loader.py   ← carrega dag_factory.yaml no Airflow
│   │   ├── integration_bridge_dag.py
│   │   └── dbt/                    ← sem mudança
│   ├── extractors/
│   │   ├── base.py                 ← GenericExtractor (substitui os ClienteXXX)
│   │   └── pdf_extractor.py        ← mantido (PDFs têm lógica própria)
│   ├── storage/
│   │   ├── bronze.py               ← MinIO client
│   │   └── silver.py               ← PostgreSQL write/read
│   ├── catalog/
│   │   └── catalog.py              ← Table Catalog read/write
│   ├── validators/
│   │   └── schema_validator.py     ← Pandera schemas por fonte
│   ├── bridge/
│   │   └── integration_bridge.py   ← Integration Gateway
│   ├── helpers/                    ← sem mudança
│   └── plugins/
│       └── cliente_base.py         ← mantido como base do GenericExtractor
├── docs/
│   ├── architecture.md             ← este documento
│   └── adr/
│       ├── 0001-caminho-unico-de-notificacao.md
│       ├── 0002-dag-factory-config-driven.md
│       ├── 0003-bronze-store-minio.md
│       └── 0004-integration-gateway.md
└── ...
```

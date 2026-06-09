---
name: criar-dag
description: Gera o arquivo YAML de config em ingestion/configs/ para uma nova fonte de dados. Cria a configuração completa com base no tipo de fonte (api, csv_xlsx ou dump), seguindo os padrões do DAG factory do projeto. Use SEMPRE que o usuário quiser adicionar uma nova fonte ao pipeline de ingestão. Disparar quando o usuário disser "adiciona nova fonte", "cria um DAG para", "quero ingerir dados de", "conecta a API X", ou descrever uma nova origem de dados que precisa ser ingerida.
input:
  - type: text
    description: Descrição da fonte (URL, tipo de auth, paginação, campos relevantes)
output:
  - type: yaml
    path: "ingestion/configs/{source_name}.yaml"
---

## Contexto do projeto

```
PROJECT_ROOT = /home/bottinolucas/Workspace/unb/tcc/Integracao-de-Dados-com-Modelos-de-Linguagem
CONFIGS_DIR  = ingestion/configs/
```

Esta skill gera o YAML de configuração para uma nova fonte de dados. O DAG factory (`ingestion/dags/`) detecta automaticamente o arquivo criado e gera o DAG correspondente — nenhum arquivo Python precisa ser alterado.

---

## Entrada esperada

O usuário pode fornecer:
- URL da API e detalhes de autenticação
- Caminho de arquivo CSV/XLSX local
- String de conexão e query SQL (para dumps de banco)
- Descrição em linguagem natural da fonte

Exemplos de input:
```
API do Portal da Transparência, endpoint /empenhos, auth por api_key no header chave-api, paginação page_number
dados/servidores.csv com separador ponto-e-vírgula
banco MSSQL SIAPE, query SELECT * FROM servidores
```

---

## O que fazer

### 1. Identificar o tipo da fonte

| Tipo | Quando usar |
|------|-------------|
| `api` | Fonte HTTP REST com JSON |
| `csv_xlsx` | Arquivo CSV ou Excel local |
| `dump` | Query SQL em banco externo |

### 2. Inferir o source_name

Derive `source_name` do nome da fonte em snake_case. Exemplos:
- Portal da Transparência empenhos → `portaltransparencia_empenhos`
- BACEN Taxa SELIC → `bacen_selic`
- SIAPE Servidores → `siape_servidores`

### 3. Gerar o YAML

#### Para `type: api`

```yaml
source_name: {source_name}
type: api
schedule: "@daily"              # ajuste conforme necessidade

url: "{url_completa}"

# HTTP auth strategy: none | bearer | api_key_header
auth_strategy: {auth_strategy}
# Se bearer ou api_key_header:
# auth_env_var: NOME_DA_ENV_VAR
# Se api_key_header:
# auth_header: nome-do-header

# Pagination strategy: none | page_number | cursor | offset
pagination_strategy: {pagination_strategy}
# Se page_number:
# page_param: pagina
# page_size: 100
# page_size_param: quantidade

# Query params estáticos (opcional)
# params:
#   ano: 2024

# Caminho pontilhado para a lista de registros no JSON (opcional)
# records_path: data

# Campo booleano de controle de paginação (opcional)
# has_more_field: hasNext
```

#### Para `type: csv_xlsx`

```yaml
source_name: {source_name}
type: csv_xlsx
schedule: "@monthly"

file_path: /opt/airflow/data/{arquivo}
separator: ";"                  # ";" ou ","
encoding: utf-8                 # utf-8 ou latin-1
```

#### Para `type: dump`

```yaml
source_name: {source_name}
type: dump
schedule: "@monthly"

connection_env: {NOME_DA_ENV_CONN}  # env var com a connection string
query: >
  SELECT *
  FROM {tabela}
```

### 4. Validações antes de salvar

- `source_name` deve ser snake_case, sem espaços ou caracteres especiais
- `url` deve ser completa (incluindo https://)
- `auth_env_var` deve ser em SCREAMING_SNAKE_CASE
- `schedule` deve ser cron válido ou alias Airflow (`@daily`, `@weekly`, `@monthly`, `@hourly`)
- Se `pagination_strategy` for `page_number`, verificar se `page_param` está presente
- Se `auth_strategy` for `bearer` ou `api_key_header`, verificar se `auth_env_var` está presente

### 5. Exibir preview e confirmar

Antes de salvar, exibir o YAML gerado e pedir confirmação:

```
=== YAML gerado ===
[conteúdo do YAML]
===================

Fonte: {source_name} ({type})
Caminho: ingestion/configs/{source_name}.yaml

Salvar? [s/n]
```

### 6. Salvar o arquivo

Salve em `{PROJECT_ROOT}/ingestion/configs/{source_name}.yaml`.

### 7. Exibir resumo final

```
✓ Config criada: ingestion/configs/{source_name}.yaml

O DAG factory detectará automaticamente o arquivo no próximo deploy.
DAG gerado: ingest_api_{source_name}   (ou ingest_csv_xlsx_*, ingest_dump_*)

Próximos passos:
  1. Adicione a env var {auth_env_var} ao .env (se autenticação configurada)
  2. Acesse Airflow UI → ative o DAG ingest_{type}_{source_name}
  3. Trigger DAG para validar a extração
  4. Crie o modelo dbt com /criar-dbt para transformar os dados
```

---

## Cuidados

- **Nunca** inclua tokens ou senhas no YAML — apenas nomes de env vars
- Fontes governamentais brasileiras frequentemente usam `latin-1` — pergunte se não souber
- APIs do Portal da Transparência usam `chave-api` como header name e paginação `page_number` com campo `hasNext`
- Para APIs sem paginação, use `pagination_strategy: none`
- O `dag_id` gerado será `ingest_{type}_{source_name}` (exceto para `api_series` que usa `ingest_{source_name}`)

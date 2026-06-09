---
name: criar-dbt
description: Gera o modelo dbt SQL na camada correta (bronze, silver ou gold) em transformation/models/. Segue as convenções do projeto gov_hub (incremental para bronze, table para silver/gold). Use SEMPRE que o usuário quiser criar uma transformação SQL para dados já ingeridos. Disparar quando o usuário disser "cria o modelo dbt", "transforma os dados de", "quero o silver de", "preciso do gold de", "adiciona modelo para", ou quando mencionar uma fonte recém-ingerida que ainda não tem modelo de transformação.
input:
  - type: text
    description: Nome da fonte ou tabela de origem e camada desejada (bronze/silver/gold)
output:
  - type: sql
    path: "transformation/models/{layer}/{model_name}.sql"
  - type: yaml
    path: "transformation/models/{layer}/{model_name}.yml"
    optional: true
---

## Contexto do projeto

```
PROJECT_ROOT  = /home/bottinolucas/Workspace/unb/tcc/Integracao-de-Dados-com-Modelos-de-Linguagem
MODELS_DIR    = transformation/models/
DBT_PROJECT   = gov_hub
```

Projeto dbt: `gov_hub` com três camadas:
- **Bronze** — staging incremental (replica do warehouse raw/staging)
- **Silver** — limpeza, tipagem forte, enriquecimento (join com outras fontes)
- **Gold** — agregações e métricas prontas para consumo (painéis, relatórios)

---

## Entrada esperada

O usuário pode fornecer:
- Nome da fonte (ex: `siafi_empenhos`)
- Nome da tabela de origem (ex: `bacen_sgs.taxa_selic`)
- Camada desejada (bronze, silver ou gold)
- Transformações desejadas em linguagem natural

Exemplos:
```
bronze para a tabela siafi_empenhos
silver do bacen_sgs com limpeza de valores nulos
gold de financiamentos imobiliários agregado por mês e tipo
```

Se o usuário não especificar a camada, pergunte antes de prosseguir.

---

## O que fazer

### 1. Identificar a camada e o modelo de origem

| Camada | Origem | Materialização |
|--------|--------|----------------|
| bronze | `source('silver', '{tabela_staging}')` | `incremental` |
| silver | `ref('{modelo_bronze}')` | `table` |
| gold | `ref('{modelo_silver}')` | `table` |

### 2. Inferir o nome do modelo

Use o padrão: `{source_name}_{descricao_opcional}`.

Exemplos:
- Bronze de siafi_empenhos → `siafi_empenhos`
- Silver enriquecido → `siafi_empenhos_enriched`
- Gold painel → `painel_empenhos_mensal`

### 3. Gerar o SQL do modelo

#### Bronze — incremental

```sql
{{ config(
    materialized='incremental',
    unique_key='{chave_primaria}',
    on_schema_change='sync_all_columns'
) }}

select *
from {{ source('silver', '{tabela_staging}') }}

{% if is_incremental() %}
  where dt_ingest > (select max(dt_ingest) from {{ this }})
{% endif %}
```

- Substituir `{chave_primaria}` pelo identificador único da tabela (ex: `num_empenho`, `codigo_serie`)
- Usar `dt_ingest` como coluna de controle incremental (deve existir na staging)
- Se a tabela não tiver `dt_ingest`, perguntar ao usuário qual coluna usar

#### Silver — table com limpeza

```sql
{{ config(materialized='table') }}

select
    {colunas_tipadas_e_renomeadas}
from {{ ref('{modelo_bronze}') }}
where {filtros_de_qualidade}
```

Regras de limpeza a aplicar:
- `cast({col} as numeric)` para colunas monetárias
- `cast({col} as date)` para colunas de data
- `lower(trim({col}))` para strings categóricas
- `nullif({col}, '')` para valores vazios → NULL
- Filtros de qualidade: `where {col_chave} is not null`

Para joins com outras fontes: use `{{ ref(...) }}` para modelos dbt ou `{{ source(...) }}` para tabelas de staging.

#### Gold — table com agregações

```sql
{{ config(materialized='table') }}

select
    {dimensoes},
    {expressoes_de_data},           -- ex: date_trunc('month', dt_emissao)
    sum({valor}) as {metrica},
    count(*) as qtd_registros
from {{ ref('{modelo_silver}') }}
{joins_opcionais}
group by {dimensoes}, {expressoes_de_data}
order by {expressoes_de_data} desc
```

### 4. Gerar schema.yml (opcional mas recomendado)

Se o usuário quiser documentação e testes, gere também o `schema.yml`:

```yaml
version: 2

models:
  - name: {model_name}
    description: "{descricao_curta}"
    columns:
      - name: {col_chave}
        description: "{descricao}"
        tests:
          - not_null
          - unique         # apenas para bronze (unique_key)
      - name: {col_valor}
        description: "{descricao}"
        tests:
          - not_null
```

### 5. Exibir preview e confirmar

```
=== Modelo gerado: transformation/models/{layer}/{model_name}.sql ===
[conteúdo SQL]
=====================================================================

Camada     : {layer}
Modelo     : {model_name}
Materializ.: {materialized}
Origem     : {source_ref}

Salvar? [s/n]
```

### 6. Salvar o(s) arquivo(s)

- SQL: `{PROJECT_ROOT}/transformation/models/{layer}/{model_name}.sql`
- YAML: `{PROJECT_ROOT}/transformation/models/{layer}/{model_name}.yml` (se gerado)

### 7. Exibir resumo final

```
✓ Modelo criado: transformation/models/{layer}/{model_name}.sql

Para executar:
  dbt run --select {model_name}
  dbt test --select {model_name}

Próximos passos sugeridos:
{lista de próximos modelos na cadeia — ex: se criou bronze, sugira criar silver}
```

---

## Cuidados

- **Bronze nunca tem lógica de negócio** — só filtragem incremental, sem transformações
- **Silver não deve ter agregações** — guarda granularidade máxima dos dados limpos
- **Gold é a camada de consumo** — pode ter múltiplos joins e agregações complexas
- Colunas monetárias no SIAFI/SIAPE podem usar vírgula como separador decimal (formato BR)
- Tabelas governamentais frequentemente têm colunas genéricas (`campo1`, `vl_lancamento`) — peça ao usuário para confirmar a semântica antes de nomear no silver
- Sempre use `{{ ref(...) }}` para referenciar outros modelos dbt — nunca hardcode schema.table
- O `unique_key` no bronze deve ser a chave natural da fonte (não um surrogate key)

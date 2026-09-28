# ADR 0008 — Source Registry como contrato entre as camadas

**Status:** Aceito

## Contexto

O YAML de fonte já dirigia a ingestão (ADR 0002), mas parava ali. Para a transformação e a integração, cada fonte ainda exigia passos manuais: exportar CSV, escrever `sources.yml` e model bronze no dbt, apontar a integração para o arquivo certo. Além disso, o silver no DuckDB grava uma tabela por dia (`<fonte>_YYYYMMDD`), um nome que o dbt não consegue referenciar de forma estável. Havia também quatro cópias da função que lê os YAMLs, uma em cada DAG.

## Decisão

O YAML do Source Registry passa a ser o contrato de ponta a ponta, lido por um único módulo (`govhub.ingestion.registry`). Três campos opcionais estendem o contrato:

| Campo | Padrão | Uso |
|---|---|---|
| `target_table` | `source_name` normalizado | Nome estável da tabela em `silver.<target_table>` no PostgreSQL |
| `silver_dataset` | `silver://<target_table>` | Dataset Airflow publicado após a sincronização |
| `dbt_packages` | — | Pacotes dbt disparados pelo dataset (DAG factory) |

A data sai do nome da tabela e vira dado: colunas `dt_ingest` (timestamp da carga) e `_silver_table` (tabela DuckDB de origem, usada como identificador do lote).

## Alternativa rejeitada

Manter o nome datado e resolver a tabela "mais recente" no dbt via macro. Rejeitado porque espalha a regra de nomeação por SQL e Python e impede declarar o source estaticamente.

## Consequências

- Adicionar uma fonte continua custando só um YAML — agora até a integração.
- Todos os campos novos têm padrão: os YAMLs existentes seguem válidos sem alteração.
- DAGs de ingestão, DAG factory e gerador do dbt compartilham `load_configs`, `target_table` e `silver_dataset`, sem divergência de regra.

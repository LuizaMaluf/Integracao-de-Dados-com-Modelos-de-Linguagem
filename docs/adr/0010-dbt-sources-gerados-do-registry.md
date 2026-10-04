# ADR 0010 — Sources e models bronze do dbt gerados a partir do Source Registry (Costura B)

**Status:** Descontinuada (2026-10-03) — fora do escopo do TCC; ver `docs/specs/limpeza-escopo.md`. Status anterior: Aceito.

## Contexto

Para cada fonte nova era preciso escrever à mão uma entrada em `sources.yml` e um model bronze no dbt. O `dbt-codegen` oficial gera esses arquivos por introspecção do banco — ou seja, depende de a tabela já existir e ignora o Source Registry.

## Decisão

`govhub.sync.dbt_source_generator` gera, a partir dos YAMLs do registry:

- `dbt/models/bronze/_generated/_sources.yml` — source `registry` (schema `silver`) com uma tabela por fonte;
- `dbt/models/bronze/_generated/<target_table>.sql` — model incremental com `incremental_strategy='delete+insert'` e `unique_key='_silver_table'`, filtrando por `dt_ingest`.

Regras de convivência com o código escrito à mão:

- O gerador só escreve em `_generated/` e só sobrescreve ou remove arquivos com o cabeçalho `GERADO`.
- O source gerado se chama `registry`, não `silver`, para não colidir com o `sources.yml` manual.
- Se já existe um model manual com o mesmo nome, a fonte é pulada (o manual prevalece).

## Alternativa rejeitada

`dbt-codegen` por introspecção. Rejeitado porque gerar a partir do YAML é o que sustenta a tese de portabilidade por configuração: a fonte é declarada uma vez, antes de existir no banco.

## Consequências

- Uma fonte nova chega ao dbt sem SQL escrito à mão (`make dbt-generate`).
- A chave de lote torna o bronze idempotente por carga: reprocessar um lote substitui as linhas dele.
- Models silver/gold continuam manuais — o gerador cobre só a camada bronze.

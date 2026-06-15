# ADR 0010 — Estender o princípio config-driven à camada de transformação

**Status:** Proposto

## Contexto

A PoC de viabilidade ponta a ponta (2026-06-15, ver `docs/pocs/01-viabilidade-e2e/poc-viabilidade-e2e.md`) confirmou que a promessa "adicionar uma fonte = só um YAML" vale na camada de ingestão, mas **não se estende à transformação dbt**. Os sources (`transformation/models/bronze/sources.yml`) e os models são escritos à mão, hardcoded nas fontes SIAFI/Transfere/Compras. Ao ingerir uma fonte nova (IBGE) via o pipeline config-driven, o dado chegou ao PostgreSQL, mas o dbt não tinha como reconhecê-lo: foi necessário escrever manualmente uma entrada de source e um model `.sql` por camada para o dado atravessar.

## Decisão

Proposta (ainda não implementada): gerar os sources e os models bronze do dbt a partir do mesmo Source Registry (YAMLs em `ingestion/configs/`) que alimenta a ingestão, de modo que adicionar uma fonte nova não exija SQL escrito à mão na camada bronze. A transformação semântica (silver/gold) permanece manual por exigir conhecimento de domínio.

## Alternativa rejeitada

Manter a transformação inteiramente manual e documentar o passo como esperado. Rejeitada porque contradiz o princípio config-driven que sustenta a tese de portabilidade do projeto — uma fonte nova deveria fluir até o bronze sem código por fonte.

## Consequências

- Fecha a "Costura B" identificada na PoC: a portabilidade passa a valer da ingestão até o bronze.
- Exige um gerador (factory) que leia os YAMLs e produza `sources.yml` + models bronze — análogo ao DAG Factory de ingestão e ao Transformation DAG Factory.
- A camada silver/gold continua exigindo trabalho manual por fonte; o ganho se limita ao bronze.
- Enquanto não implementado, cada fonte nova exige source + model bronze à mão (custo medido na PoC: ~8 linhas por fonte).

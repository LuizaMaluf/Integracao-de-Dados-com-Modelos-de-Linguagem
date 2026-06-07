# ADR 0002 — Substituir DAGs individuais por DAG Factory config-driven

**Status:** Proposto

## Contexto

O projeto acumulou 73 arquivos de DAG individuais para 14 fontes governamentais. Cada fonte tem 3–8 DAGs quase idênticos (um por endpoint), cada um com um `ClienteXXX` próprio. Adicionar uma nova fonte requer criar 5+ arquivos Python, duplicar lógica de retry/paginação/auth e registrar manualmente no Airflow.

O padrão atual é hard-coded e não escala: quanto mais fontes, mais arquivos; qualquer mudança transversal (ex: ajustar retry delay) exige editar dezenas de arquivos.

## Decisão

Substituir os 73 arquivos de DAG e os 15+ `ClienteXXX` por um pipeline config-driven:

1. **Source Registry**: um arquivo YAML por fonte em `airflow_lappis/configs/`. Declara URL, auth, estratégia de paginação, schema alvo, schedule e campos de conflito.
2. **DAG Factory**: `astronomer/dag-factory` lê um `dag_factory.yaml` central e gera os DAGs automaticamente. Nenhum arquivo Python de DAG por fonte.
3. **Generic Extractor**: uma classe `GenericExtractor` em `extractors/base.py` substitui todos os `ClienteXXX`. Estende a `ClienteBase` existente e parametriza paginação e auth via config.

Adicionar uma fonte nova = criar um YAML de ~20 linhas. Nenhum arquivo Python.

## Alternativa rejeitada

Manter o padrão atual e adicionar um gerador de código que escreve os arquivos de DAG a partir de templates. Rejeitado porque o problema de proliferação de arquivos permanece — só muda quem os escreve. Manutenção e revisão continuam custosos.

## Consequências

- Os 73 DAGs existentes precisam ser migrados para o Source Registry. A migração pode ser feita incrementalmente por grupo de fonte.
- `dag-factory` adiciona uma dependência nova. É open source (Apache 2.0), mantido pela Astronomer, com adoção ampla em produção.
- DAGs com lógica muito específica (ex: PDFs semânticos, dumps SQL) podem não caber no Generic Extractor e precisarão de DAGs Python próprios — mas são exceção, não regra.
- A `ClienteBase` existente é mantida como base do Generic Extractor — sem reescrita.

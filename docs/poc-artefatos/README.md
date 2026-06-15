# Artefatos da PoC de Viabilidade E2E

Evidências **capturadas dos logs do sistema vivo** durante e após a execução da PoC (2026-06-15). Cada `.log` é saída real de comando — não texto redigido. Embasam o documento [../poc-viabilidade-e2e.md](../poc-viabilidade-e2e.md).

| Artefato | Evidência | O que prova |
|---|---|---|
| [01-camada1-dags-config-driven.log](01-camada1-dags-config-driven.log) | `airflow dags list` | 5 DAGs `ingest_api_*` gerados, 1 por YAML, zero código de DAG |
| [02-camada1-execucao-dag-ibge.log](02-camada1-execucao-dag-ibge.log) | `tasks states-for-dag-run` | extract→write_bronze→stage_silver = success no Airflow real |
| [03-camada1-bronze-silver.log](03-camada1-bronze-silver.log) | `mc ls` + query DuckDB | bronze parquet 170KiB em MinIO + 5.571 linhas reais no silver |
| [04-camada2-dbt-run.log](04-camada2-dbt-run.log) | `dbt run` | `INSERT 0 5571`, `Completed successfully` — mas source+model à mão (Costura B) |
| [05-camada3-decision-layer-llm.log](05-camada3-decision-layer-llm.log) | `poc_e2e_ibge.json` | LLM escolheu `uf_id↔id` (match 0%) e rejeitou a Derived Key de maior score |
| [07-bugs-corrigidos.log](07-bugs-corrigidos.log) | erros + estado pós-fix | 4 bugs que provam que a arquitetura nunca rodou E2E |

## Como reproduzir

Os artefatos foram gerados com a stack de pé (`cd ingestion && docker compose up -d` + `poc-analytics-pg`). Os comandos exatos de captura estão no cabeçalho (`#`) de cada `.log`.

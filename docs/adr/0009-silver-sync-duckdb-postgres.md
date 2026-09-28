# ADR 0009 — Silver Sync: ponte automática DuckDB → PostgreSQL (Costura A)

**Status:** Aceito

## Contexto

A ingestão grava o silver em DuckDB; o dbt e a integração leem do PostgreSQL. Na PoC de viabilidade (IBGE), a cópia entre os dois foi feita por um script ad-hoc. Sem uma ponte permanente, cada nova fonte exige intervenção manual para chegar ao dbt.

## Decisão

Cada DAG de ingestão ganha a task `sync_postgres`, logo após `stage_silver`, que chama `govhub.sync.silver_sync.sync_to_postgres`:

1. Lê a tabela do lote no DuckDB (`<fonte>_YYYYMMDD`).
2. Serializa colunas aninhadas (struct/list) como JSON em texto.
3. Adiciona `dt_ingest` (UTC) e `_silver_table` (nome do lote).
4. Em uma transação: cria o schema se preciso, cria colunas novas como `TEXT`, apaga linhas do mesmo lote (`_silver_table`) e insere o lote (append).

A task declara `outlets=[Dataset(silver_dataset)]`, o que dispara a transformação da fonte (data-aware scheduling, já suportado pela DAG factory).

## Alternativas rejeitadas

- **PostgreSQL como silver único** (sem DuckDB): simplificaria a arquitetura, mas acopla a ingestão a um banco externo e perde o staging local barato. Preservar o DuckDB foi escolha explícita.
- **`if_exists="replace"`**: simples, mas destrói o histórico que o bronze incremental do dbt precisa para ser incremental.

## Consequências

- Re-executar a ingestão no mesmo dia é idempotente: o lote é substituído, não duplicado.
- Colunas aninhadas chegam como texto JSON; converter para `JSONB` fica para quando algum model precisar consultar dentro delas.
- Colunas novas na fonte não quebram a carga; o tipo definitivo é responsabilidade do dbt (silver).

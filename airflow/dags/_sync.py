"""
Task compartilhada da costura A (Silver Sync), usada pelas DAGs de ingestão.

Não define DAGs. Fica em ``dags/`` porque o Airflow já coloca essa pasta no
``sys.path``; as DAGs importam com ``from _sync import ...``.
"""
from airflow.datasets import Dataset
from airflow.decorators import task

from govhub.ingestion import registry


def sync_postgres(cfg: dict):
    """Task que sincroniza um lote DuckDB → silver.<target_table> no Postgres.

    Publica o Dataset da fonte, disparando a transformação (DAG factory).
    Recebe o nome do lote retornado por ``stage_silver``.
    """

    @task(task_id="sync_postgres", outlets=[Dataset(registry.silver_dataset(cfg))])
    def _sync(duckdb_table: str) -> int:
        from govhub.sync.silver_sync import airflow_task

        return airflow_task(cfg, duckdb_table)

    return _sync


def sync_postgres_many(cfg: dict):
    """Variante para dumps: recebe ``[[lote_duckdb, nome_da_tabela], ...]``."""

    @task(task_id="sync_postgres", outlets=[Dataset(registry.silver_dataset(cfg))])
    def _sync(lotes: list) -> int:
        from govhub.sync.silver_sync import sync_to_postgres

        return sum(
            sync_to_postgres(lote, registry.normalize_name(tabela)) for lote, tabela in lotes
        )

    return _sync

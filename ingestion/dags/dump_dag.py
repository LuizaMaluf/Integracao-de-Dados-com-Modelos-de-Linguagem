"""
DAG: Database dump ingestion.
Discovers all configs of type dump in /opt/airflow/configs/.
Flow: parse dump → write bronze (one Parquet per table) → stage each to silver
"""
from airflow.decorators import dag, task

from ingestion.dags.factory import register_dags
from core.extractors.factory import get_extractor
from core.providers.factory import get_storage


def dag_factory(cfg: dict):
    @dag(
        dag_id=f"ingest_dump_{cfg['source_name']}",
        schedule=cfg.get("schedule", "@weekly"),
        catchup=False,
        tags=["ingestion", "dump"],
    )
    def ingest():
        @task()
        def extract() -> dict:
            tables = get_extractor(cfg).extract()
            return {name: df.to_json() for name, df in tables.items()}

        @task()
        def write_bronze(tables_json: dict) -> list[str]:
            import pandas as pd
            keys = []
            for table_name, df_json in tables_json.items():
                df = pd.read_json(df_json)
                key = get_storage().write_parquet(df, cfg["source_name"], table_name)
                keys.append(key)
            return keys

        @task()
        def stage_silver(bronze_keys: list):
            from storage import silver
            for key in bronze_keys:
                table_name = key.split("/")[-3]
                df = get_storage().read_parquet(key)
                silver.write(df, table_name)

        stage_silver(write_bronze(extract()))

    return ingest()


register_dags("dump", dag_factory, globals())

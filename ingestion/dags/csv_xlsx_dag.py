"""
DAG: CSV / XLSX ingestion.
Discovers all configs of type csv_xlsx in /opt/airflow/configs/.
Flow: extract → write bronze → stage to silver
"""
from airflow.decorators import dag, task

from ingestion.dags.factory import register_dags
from core.extractors.factory import get_extractor
from core.providers.factory import get_storage


def dag_factory(cfg: dict):
    @dag(
        dag_id=f"ingest_csv_{cfg['source_name']}",
        schedule=cfg.get("schedule", "@daily"),
        catchup=False,
        tags=["ingestion", "csv"],
    )
    def ingest():
        @task()
        def extract():
            return get_extractor(cfg).extract().to_json()

        @task()
        def write_bronze(df_json: str):
            import pandas as pd
            df = pd.read_json(df_json)
            return get_storage().write_parquet(df, cfg["source_name"], "data")

        @task()
        def stage_silver(bronze_key: str):
            from storage import silver
            df = get_storage().read_parquet(bronze_key)
            return silver.write(df, cfg["source_name"])

        key = write_bronze(extract())
        stage_silver(key)

    return ingest()


register_dags("csv_xlsx", dag_factory, globals())

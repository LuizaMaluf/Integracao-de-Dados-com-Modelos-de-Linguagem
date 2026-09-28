"""
DAG: REST API ingestion.
Discovers all configs of type api in /opt/airflow/configs/.
Flow: fetch all pages → write bronze → stage to silver → sync Postgres
"""
from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task

from govhub.ingestion import registry

from _sync import sync_postgres

CONFIGS_DIR = Path("/opt/airflow/configs")


def _load_configs():
    return registry.load_configs(CONFIGS_DIR, types=("api",))


for _cfg in _load_configs():
    _source = _cfg["source_name"]
    # Montada com o dict da fonte: dentro de _make_dag, cfg vira DagParam.
    _sync_postgres = sync_postgres(_cfg)

    @dag(
        dag_id=f"ingest_api_{_source}",
        schedule=_cfg.get("schedule", "@daily"),
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["ingestion", "api"],
    )
    def _make_dag(cfg=_cfg):
        @task()
        def extract(cfg):
            from govhub.ingestion.extractors.api_extractor import ApiExtractor
            return ApiExtractor(cfg).extract().to_json()

        @task()
        def write_bronze(df_json: str, cfg):
            import pandas as pd
            from govhub.ingestion.storage import bronze
            df = pd.read_json(df_json)
            return bronze.write_parquet(df, cfg["source_name"], "data.parquet")

        @task()
        def stage_silver(bronze_key: str, cfg):
            from govhub.ingestion.storage import bronze, silver
            df = bronze.read_parquet(bronze_key)
            return silver.write(df, cfg["source_name"])

        @task()
        def run_annotate_context(df_json: str, cfg):
            import pandas as pd
            from govhub.ingestion.context.annotate_context import annotate_from_df
            df = pd.read_json(df_json)
            table_name = f"{cfg.get('target_schema', 'silver')}.{cfg['source_name']}"
            annotate_from_df(table_name, df, store=None)  # store=None: sem DB em dev

        @task()
        def run_profile_table(df_json: str, cfg):
            import pandas as pd
            from govhub.ingestion.context.profile_context import profile_table
            df = pd.read_json(df_json)
            table_name = f"{cfg.get('target_schema', 'silver')}.{cfg['source_name']}"
            profile_table(table_name, df, store=None)  # store=None: sem DB em dev

        df_result = extract(cfg)
        key = write_bronze(df_result, cfg)
        _sync_postgres(stage_silver(key, cfg))
        run_annotate_context(df_result, cfg)
        run_profile_table(df_result, cfg)

    globals()[f"ingest_api_{_source}"] = _make_dag()

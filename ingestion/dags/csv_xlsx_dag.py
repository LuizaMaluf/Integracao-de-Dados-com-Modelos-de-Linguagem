"""
DAG: CSV / XLSX ingestion.
Discovers all configs of type csv or xlsx in /opt/airflow/configs/
and creates one DAG per source dynamically.
Flow: extract → write bronze → stage to silver
"""
import sys
from pathlib import Path

import yaml
from airflow.decorators import dag, task

sys.path.insert(0, "/opt/airflow")

CONFIGS_DIR = Path("/opt/airflow/configs")


def _load_configs():
    return [
        yaml.safe_load(f.read_text())
        for f in CONFIGS_DIR.glob("*.yaml")
        if yaml.safe_load(f.read_text()).get("type") in ("csv", "xlsx")
    ]


for _cfg in _load_configs():
    _source = _cfg["source_name"]

    @dag(
        dag_id=f"ingest_csv_{_source}",
        schedule=_cfg.get("schedule", "@daily"),
        catchup=False,
        tags=["ingestion", "csv"],
    )
    def _make_dag(cfg=_cfg):
        @task()
        def extract(cfg):
            from extractors.csv_extractor import CsvExtractor
            return CsvExtractor(cfg).extract().to_json()

        @task()
        def write_bronze(df_json: str, cfg):
            import pandas as pd
            from storage import bronze
            df = pd.read_json(df_json)
            return bronze.write_parquet(df, cfg["source_name"], "data.parquet")

        @task()
        def stage_silver(bronze_key: str, cfg):
            from storage import bronze, silver
            df = bronze.read_parquet(bronze_key)
            return silver.write(df, cfg["source_name"])

        @task()
        def run_annotate_context(df_json: str, cfg):
            import pandas as pd
            from context.annotate_context import annotate_from_df
            df = pd.read_json(df_json)
            table_name = f"{cfg.get('target_schema', 'silver')}.{cfg['source_name']}"
            annotate_from_df(table_name, df, store=None)  # store=None: sem DB em dev

        @task()
        def run_profile_table(df_json: str, cfg):
            import pandas as pd
            from context.profile_context import profile_table
            df = pd.read_json(df_json)
            table_name = f"{cfg.get('target_schema', 'silver')}.{cfg['source_name']}"
            profile_table(table_name, df, store=None)  # store=None: sem DB em dev

        df_result = extract(cfg)
        key = write_bronze(df_result, cfg)
        stage_silver(key, cfg)
        run_annotate_context(df_result, cfg)
        run_profile_table(df_result, cfg)

    globals()[f"ingest_csv_{_source}"] = _make_dag()

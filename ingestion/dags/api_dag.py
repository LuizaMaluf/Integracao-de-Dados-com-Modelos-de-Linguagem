"""
DAG: REST API ingestion.
Discovers all configs of type api in /opt/airflow/configs/.
Flow: fetch all pages → write bronze → stage to silver
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
        if yaml.safe_load(f.read_text()).get("type") == "api"
    ]


for _cfg in _load_configs():
    _source = _cfg["source_name"]

    @dag(
        dag_id=f"ingest_api_{_source}",
        schedule=_cfg.get("schedule", "@daily"),
        catchup=False,
        tags=["ingestion", "api"],
    )
    def _make_dag(cfg=_cfg):
        @task()
        def extract(cfg):
            from extractors.api_extractor import ApiExtractor
            return ApiExtractor(cfg).extract().to_json()

        @task()
        def write_bronze(df_json: str, cfg):
            import pandas as pd
            from providers import get_storage
            df = pd.read_json(df_json)
            return get_storage().write_parquet(df, cfg["source_name"], "data")

        @task()
        def stage_silver(bronze_key: str, cfg):
            from providers import get_storage
            from storage import silver
            df = get_storage().read_parquet(bronze_key)
            return silver.write(df, cfg["source_name"])

        key = write_bronze(extract(cfg), cfg)
        stage_silver(key, cfg)

    globals()[f"ingest_api_{_source}"] = _make_dag()

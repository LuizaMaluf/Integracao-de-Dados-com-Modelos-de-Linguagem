"""
DAG: Database dump ingestion.
Discovers all configs of type dump in /opt/airflow/configs/.
Flow: parse dump → write bronze (one Parquet per table) → stage each to silver
"""
from pathlib import Path

from airflow.decorators import dag, task

from govhub.ingestion import registry

CONFIGS_DIR = Path("/opt/airflow/configs")


def _load_configs():
    return registry.load_configs(CONFIGS_DIR, types=("dump",))


for _cfg in _load_configs():
    _source = _cfg["source_name"]

    @dag(
        dag_id=f"ingest_dump_{_source}",
        schedule=_cfg.get("schedule", "@weekly"),
        catchup=False,
        tags=["ingestion", "dump"],
    )
    def _make_dag(cfg=_cfg):
        @task()
        def extract(cfg) -> dict:
            from govhub.ingestion.extractors.dump_extractor import DumpExtractor
            # Returns {table_name: df_json_string}
            tables = DumpExtractor(cfg).extract()
            return {name: df.to_json() for name, df in tables.items()}

        @task()
        def write_bronze(tables_json: dict, cfg) -> list[str]:
            import pandas as pd
            from govhub.ingestion.storage import bronze
            keys = []
            for table_name, df_json in tables_json.items():
                df = pd.read_json(df_json)
                key = bronze.write_parquet(df, cfg["source_name"], f"{table_name}.parquet")
                keys.append(key)
            return keys

        @task()
        def stage_silver(bronze_keys: list, cfg):
            from govhub.ingestion.storage import bronze, silver
            for key in bronze_keys:
                table_name = key.split("/")[-1].replace(".parquet", "")
                df = bronze.read_parquet(key)
                silver.write(df, table_name)

        keys = write_bronze(extract(cfg), cfg)
        stage_silver(keys, cfg)

    globals()[f"ingest_dump_{_source}"] = _make_dag()

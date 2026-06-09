"""
DAG: multi-series REST API ingestion.
Discovers all configs of type 'api_series' in /opt/airflow/configs/.
For each config, generates one DAG with four tasks per series:
  extract_<codigo> → write_original_<codigo> → convert_parquet_<codigo> → load_bronze_<codigo>

Provider selection (storage + warehouse) is driven by CLIENT_NAME env var
pointing to a clients/<name>.yaml file. No provider logic lives here.
"""
import sys
from datetime import datetime
from pathlib import Path

import yaml
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup

sys.path.insert(0, "/opt/airflow")

CONFIGS_DIR = Path("/opt/airflow/configs")


def _load_series_configs() -> list[dict]:
    if not CONFIGS_DIR.exists():
        return []
    configs = []
    for f in CONFIGS_DIR.glob("*.yaml"):
        cfg = yaml.safe_load(f.read_text())
        if cfg.get("type") == "api_series":
            configs.append(cfg)
    return configs


def _create_dag(cfg: dict):
    source = cfg["source_name"]
    start_date = datetime.fromisoformat(cfg["start_date"]) if "start_date" in cfg else days_ago(1)

    @dag(
        dag_id=f"ingest_{source}",
        schedule=cfg.get("schedule", "@daily"),
        start_date=start_date,
        catchup=False,
        tags=["ingestion", "api_series", source],
    )
    def _dag_func():
        prev_group = None
        for serie in cfg["series"]:
            codigo = serie["codigo"]

            with TaskGroup(group_id=f"serie_{codigo}") as tg:

                @task(task_id=f"extract_{codigo}")
                def extract(serie=serie):
                    from extractors import get_extractor
                    return get_extractor({**cfg, "serie": serie}).extract_raw()

                @task(task_id=f"write_original_{codigo}")
                def write_original(raw_json: str, serie=serie):
                    from providers import get_storage
                    return get_storage().write_raw(raw_json, cfg["source_name"], serie["codigo"], "json")

                @task(task_id=f"convert_parquet_{codigo}")
                def convert_parquet(original_key: str, serie=serie):
                    from providers import get_storage
                    return get_storage().convert_to_parquet(original_key)

                @task(task_id=f"load_bronze_{codigo}")
                def load_bronze(parquet_key: str, serie=serie):
                    from providers import get_warehouse
                    get_warehouse().load_from_parquet(parquet_key, cfg["source_name"], serie["tabela"])

                raw_json = extract()
                original_key = write_original(raw_json)
                parquet_key = convert_parquet(original_key)
                load_bronze(parquet_key)

            if prev_group is not None:
                _ = prev_group >> tg
            prev_group = tg

    return _dag_func()


for _cfg in _load_series_configs():
    globals()[f"ingest_{_cfg['source_name']}"] = _create_dag(_cfg)

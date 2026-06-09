"""
DAG: multi-series REST API ingestion.
Discovers all configs of type 'api_series' in /opt/airflow/configs/.
For each config, generates one DAG with four tasks per series:
  extract → write_original → convert_parquet → load_bronze
Series run sequentially (each group waits for the previous).
"""
from airflow.decorators import dag, task
from airflow.utils.task_group import TaskGroup

from ingestion.dags.factory import build_start_date, register_dags
from core.extractors.factory import get_extractor
from core.providers.factory import get_storage, get_warehouse


def dag_factory(cfg: dict):

    def _serie_group(serie: dict):
        codigo = serie["codigo"]
        with TaskGroup(group_id=f"serie_{codigo}") as tg:

            @task(task_id=f"extract_{codigo}")
            def extract():
                return get_extractor({**cfg, "serie": serie}).extract_raw()

            @task(task_id=f"write_original_{codigo}")
            def write_original(raw_json: str):
                return get_storage().write_raw(raw_json, cfg["source_name"], serie["codigo"], "json")

            @task(task_id=f"convert_parquet_{codigo}")
            def convert_parquet(original_key: str):
                return get_storage().convert_to_parquet(original_key)

            @task(task_id=f"load_bronze_{codigo}")
            def load_bronze(parquet_key: str):
                get_warehouse().load_from_parquet(parquet_key, cfg["source_name"], serie["tabela"])

            raw_json = extract()
            original_key = write_original(raw_json)
            parquet_key = convert_parquet(original_key)
            load_bronze(parquet_key)

        return tg

    @dag(
        dag_id=f"ingest_{cfg['source_name']}",
        schedule=cfg.get("schedule", "@daily"),
        start_date=build_start_date(cfg),
        catchup=False,
        tags=["ingestion", "api_series", cfg["source_name"]],
    )
    def ingest():
        prev_group = None
        for serie in cfg["series"]:
            tg = _serie_group(serie)
            if prev_group is not None:
                tg.set_upstream(prev_group)
            prev_group = tg

    return ingest()


register_dags("api_series", dag_factory, globals())

from datetime import timedelta

import pendulum
from airflow.decorators import dag, task

from core.contracts.pipeline import PipelineConfig
from core.extractors.stubs import get_extractor
from core.providers.stubs import get_provider


def make_dag(cfg: PipelineConfig):
    @dag(
        dag_id=cfg.dag_id,
        schedule=cfg.schedule,
        start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
        catchup=False,
        max_active_runs=1,
        tags=[cfg.tenant, cfg.source, "bronze"],
        doc_md=f"Pipeline **{cfg.dag_id}** — tenant `{cfg.tenant}`, source `{cfg.source}`.",
        default_args={
            "retries": cfg.retries,
            "retry_delay": timedelta(minutes=cfg.retry_delay_minutes),
        },
    )
    def _pipeline():
        @task()
        def extract() -> dict:
            return get_extractor(cfg.source).run(filters=cfg.filters)

        @task()
        def validate(data: dict) -> dict:
            if not data.get("records"):
                raise ValueError(f"[{cfg.dag_id}] extract returned empty records")
            return data

        @task()
        def load(data: dict) -> None:
            get_provider(cfg.destination).write(
                data, path=f"bronze/{cfg.tenant}/{cfg.source}"
            )

        load(validate(extract()))

    return _pipeline()

import pendulum

from core.utils.config import load_configs


def build_start_date(cfg: dict):
    """Returns start_date from config, defaulting to yesterday UTC."""
    if "start_date" in cfg:
        return pendulum.parse(cfg["start_date"])
    return pendulum.now("UTC").subtract(days=1)


def register_dags(source_type: str, dag_factory_fn, caller_globals: dict) -> None:
    """Loads all configs of source_type and registers one DAG per config in caller_globals."""
    for cfg in load_configs(source_type):
        dag = dag_factory_fn(cfg)
        caller_globals[dag.dag_id] = dag

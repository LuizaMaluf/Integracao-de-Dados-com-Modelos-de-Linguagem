import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from core.contracts.pipeline import PipelineConfig
from ingestion.dags._factory import make_dag

log = logging.getLogger(__name__)

_PIPELINES_DIR = Path("/opt/airflow/configs/pipelines")


def _load_all(target_globals: dict) -> None:
    if not _PIPELINES_DIR.exists():
        log.warning("Pipelines directory not found: %s", _PIPELINES_DIR)
        return

    for path in sorted(_PIPELINES_DIR.rglob("*.yaml")):
        tenant = path.parent.name
        source = path.stem
        try:
            raw = yaml.safe_load(path.read_text()) or {}
            cfg = PipelineConfig(tenant=tenant, source=source, **raw)
            target_globals[cfg.dag_id] = make_dag(cfg)
            log.info("Registered DAG: %s", cfg.dag_id)
        except ValidationError as exc:
            log.error("Config validation error  %s/%s.yaml:\n%s", tenant, source, exc)
        except Exception as exc:
            log.error("Failed to load pipeline  %s/%s.yaml: %s", tenant, source, exc)


_load_all(globals())

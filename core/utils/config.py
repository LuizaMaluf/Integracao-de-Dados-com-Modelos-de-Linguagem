from pathlib import Path

import yaml

CONFIGS_DIR = Path("/opt/airflow/configs")


def load_configs(source_type: str) -> list[dict]:
    """Return all source configs of the given type from CONFIGS_DIR."""
    if not CONFIGS_DIR.exists():
        return []
    configs = []
    for f in CONFIGS_DIR.glob("*.yaml"):
        cfg = yaml.safe_load(f.read_text())
        if cfg.get("type") == source_type:
            configs.append(cfg)
    return configs

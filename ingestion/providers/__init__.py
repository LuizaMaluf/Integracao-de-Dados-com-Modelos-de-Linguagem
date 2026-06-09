"""
Provider factory.
Reads CLIENT_NAME env var → loads clients/<name>.yaml → returns the right provider.
"""
import os
from pathlib import Path

import yaml

from .storage.base import StorageProvider
from .warehouse.base import WarehouseProvider

_CLIENTS_DIR = Path(os.environ.get("CLIENTS_DIR", "/opt/airflow/clients"))


def _load_client_config() -> dict:
    name = os.environ["CLIENT_NAME"]
    path = _CLIENTS_DIR / f"{name}.yaml"
    return yaml.safe_load(path.read_text())


def get_storage() -> StorageProvider:
    cfg = _load_client_config()["storage"]
    from .storage.minio import MinIOProvider
    from .storage.s3 import S3Provider

    registry = {
        "minio": MinIOProvider,
        "aws_s3": S3Provider,
    }
    provider_cls = registry.get(cfg["provider"])
    if provider_cls is None:
        raise ValueError(f"Unknown storage provider: '{cfg['provider']}'. Available: {list(registry)}")
    return provider_cls(cfg)


def get_warehouse() -> WarehouseProvider:
    cfg = _load_client_config()["warehouse"]
    from .warehouse.bigquery import BigQueryProvider
    from .warehouse.postgres import PostgreSQLProvider

    registry = {
        "postgres": PostgreSQLProvider,
        "bigquery": BigQueryProvider,
    }
    provider_cls = registry.get(cfg["provider"])
    if provider_cls is None:
        raise ValueError(f"Unknown warehouse provider: '{cfg['provider']}'. Available: {list(registry)}")
    return provider_cls(cfg)

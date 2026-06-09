"""
Provider factory.
Reads CLIENT_NAME env var → loads clients/<name>.yaml → returns the right provider.
"""
import os
from pathlib import Path

import yaml

from core.providers.storage.base import StorageProvider
from core.providers.storage.minio import MinIOProvider
from core.providers.storage.s3 import S3Provider
from core.providers.warehouse.base import WarehouseProvider
from core.providers.warehouse.bigquery import BigQueryProvider
from core.providers.warehouse.postgres import PostgreSQLProvider

_CLIENTS_DIR = Path(os.environ.get("CLIENTS_DIR", "/opt/airflow/clients"))

_STORAGE_REGISTRY = {
    "minio": MinIOProvider,
    "aws_s3": S3Provider,
}

_WAREHOUSE_REGISTRY = {
    "postgres": PostgreSQLProvider,
    "bigquery": BigQueryProvider,
}


def _load_client_config() -> dict:
    name = os.environ["CLIENT_NAME"]
    path = _CLIENTS_DIR / f"{name}.yaml"
    return yaml.safe_load(path.read_text())


def get_storage() -> StorageProvider:
    cfg = _load_client_config()["storage"]
    provider_cls = _STORAGE_REGISTRY.get(cfg["provider"])
    if provider_cls is None:
        raise ValueError(f"Unknown storage provider: '{cfg['provider']}'. Available: {list(_STORAGE_REGISTRY)}")
    return provider_cls(cfg)


def get_warehouse() -> WarehouseProvider:
    cfg = _load_client_config()["warehouse"]
    provider_cls = _WAREHOUSE_REGISTRY.get(cfg["provider"])
    if provider_cls is None:
        raise ValueError(f"Unknown warehouse provider: '{cfg['provider']}'. Available: {list(_WAREHOUSE_REGISTRY)}")
    return provider_cls(cfg)

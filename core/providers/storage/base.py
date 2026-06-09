"""
StorageProvider: abstract contract for object storage (raw zone).
Concrete implementations: MinIOProvider, S3Provider, ...

Storage layout per artifact:
  raw/{source_name}/{codigo}/original/{date}.{ext}   ← original format
  raw/{source_name}/{codigo}/parquet/{date}.parquet   ← converted
"""
from abc import ABC, abstractmethod

import pandas as pd


class StorageProvider(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def write_raw(self, data: bytes | str, source_name: str, codigo: str | int, ext: str) -> str:
        """Persist raw bytes or string in original format. Returns an opaque storage key."""
        ...

    @abstractmethod
    def read_raw(self, key: str) -> bytes:
        """Retrieve raw bytes by storage key."""
        ...

    @abstractmethod
    def write_parquet(self, df: pd.DataFrame, source_name: str, codigo: str | int) -> str:
        """Persist a DataFrame as Parquet. Returns an opaque storage key."""
        ...

    @abstractmethod
    def read_parquet(self, key: str) -> pd.DataFrame:
        """Retrieve a Parquet artifact by its storage key."""
        ...

    @abstractmethod
    def convert_to_parquet(self, original_key: str) -> str:
        """Read raw from storage, convert to Parquet, save in processed/staging/. Returns parquet_key."""
        ...

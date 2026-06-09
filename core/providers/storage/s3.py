"""
S3Provider: AWS S3 object storage.
Config keys: bucket_env, region
Credentials resolved via the default AWS credential chain
(env vars, ~/.aws/credentials, IAM role).
"""
import io
import os
from datetime import date

import boto3
import pandas as pd

from core.providers.storage.base import StorageProvider


class S3Provider(StorageProvider):
    def _client(self):
        raise NotImplementedError(
            "S3Provider is not yet implemented. "
        )

    def _bucket(self) -> str:
        raise NotImplementedError(
            "S3Provider is not yet implemented. "
        )

    def write_raw(self, data: bytes | str, source_name: str, codigo: str | int, ext: str) -> str:
        raise NotImplementedError(
            "S3Provider is not yet implemented. "
        )

    def read_raw(self, key: str) -> bytes:
        raise NotImplementedError(
            "S3Provider is not yet implemented. "
        )

    def write_parquet(self, df: pd.DataFrame, source_name: str, codigo: str | int) -> str:
        raise NotImplementedError(
            "S3Provider is not yet implemented. "
        )

    def read_parquet(self, key: str) -> pd.DataFrame:
        raise NotImplementedError(
            "S3Provider is not yet implemented. "
        )

    def convert_to_parquet(self, original_key: str) -> str:
        raise NotImplementedError(
            "S3Provider is not yet implemented. "
        )
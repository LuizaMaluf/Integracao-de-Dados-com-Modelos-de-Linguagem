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

from .base import StorageProvider


class S3Provider(StorageProvider):
    def _client(self):
        return boto3.client("s3", region_name=self.config.get("region", "us-east-1"))

    def _bucket(self) -> str:
        return os.environ[self.config["bucket_env"]]

    def write_raw(self, data: bytes | str, source_name: str, codigo: str | int, ext: str) -> str:
        if isinstance(data, str):
            data = data.encode()
        key = f"raw/{source_name}/{codigo}/original/{date.today().isoformat()}.{ext}"
        self._client().put_object(Bucket=self._bucket(), Key=key, Body=data)
        return key

    def read_raw(self, key: str) -> bytes:
        obj = self._client().get_object(Bucket=self._bucket(), Key=key)
        return obj["Body"].read()

    def write_parquet(self, df: pd.DataFrame, source_name: str, codigo: str | int) -> str:
        key = f"raw/{source_name}/{codigo}/parquet/{date.today().isoformat()}.parquet"
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        self._client().put_object(Bucket=self._bucket(), Key=key, Body=buf.read())
        return key

    def read_parquet(self, key: str) -> pd.DataFrame:
        obj = self._client().get_object(Bucket=self._bucket(), Key=key)
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))

    def convert_to_parquet(self, original_key: str) -> str:
        raw = self.read_raw(original_key)
        df = pd.read_json(io.BytesIO(raw), orient="records")
        parts = original_key.split("/")
        source, codigo = parts[1], parts[2]
        key = f"processed/staging/{source}/{codigo}/{date.today().isoformat()}.parquet"
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        self._client().put_object(Bucket=self._bucket(), Key=key, Body=buf.read())
        return key

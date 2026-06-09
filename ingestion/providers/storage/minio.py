"""
MinIOProvider: S3-compatible self-hosted object storage.
Config keys: endpoint_env, access_key_env, secret_key_env, bucket_env
"""
import io
import os
from datetime import date

import boto3
import pandas as pd
from botocore.client import Config

from .base import StorageProvider


class MinIOProvider(StorageProvider):
    def _client(self):
        return boto3.client(
            "s3",
            endpoint_url=f"http://{os.environ[self.config['endpoint_env']]}",
            aws_access_key_id=os.environ[self.config["access_key_env"]],
            aws_secret_access_key=os.environ[self.config["secret_key_env"]],
            config=Config(signature_version="s3v4"),
        )

    def _bucket(self) -> str:
        return os.environ[self.config["bucket_env"]]

    def _ensure_bucket(self) -> None:
        client = self._client()
        try:
            client.create_bucket(Bucket=self._bucket())
        except client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise

    def write_raw(self, data: bytes | str, source_name: str, codigo: str | int, ext: str) -> str:
        self._ensure_bucket()
        if isinstance(data, str):
            data = data.encode()
        key = f"raw/{source_name}/{codigo}/original/{date.today().isoformat()}.{ext}"
        self._client().put_object(Bucket=self._bucket(), Key=key, Body=data)
        return key

    def read_raw(self, key: str) -> bytes:
        obj = self._client().get_object(Bucket=self._bucket(), Key=key)
        return obj["Body"].read()

    def write_parquet(self, df: pd.DataFrame, source_name: str, codigo: str | int) -> str:
        self._ensure_bucket()
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
        self._ensure_bucket()
        self._client().put_object(Bucket=self._bucket(), Key=key, Body=buf.read())
        return key

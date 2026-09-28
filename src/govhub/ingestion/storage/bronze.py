"""
Bronze Zone: immutable raw artifact storage on MinIO.
Every artifact is written once and never mutated.
Path convention: raw/<source_name>/<date>/<filename>
"""
import io
import os
from datetime import date

import boto3
import pandas as pd
from botocore.client import Config


def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{os.environ['MINIO_ENDPOINT']}",
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
        config=Config(signature_version="s3v4"),
    )


def _bucket() -> str:
    return os.environ.get("MINIO_BUCKET_BRONZE", "bronze")


def write_parquet(df: pd.DataFrame, source_name: str, filename: str) -> str:
    """Upload a DataFrame as Parquet to the bronze zone. Returns the S3 key."""
    key = f"raw/{source_name}/{date.today().isoformat()}/{filename}"
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    _client().put_object(Bucket=_bucket(), Key=key, Body=buf.read())
    return key


def write_bytes(data: bytes, source_name: str, filename: str) -> str:
    """Upload raw bytes (e.g. a PDF binary) to the bronze zone. Returns the S3 key."""
    key = f"raw/{source_name}/{date.today().isoformat()}/{filename}"
    _client().put_object(Bucket=_bucket(), Key=key, Body=data)
    return key


def read_parquet(key: str) -> pd.DataFrame:
    """Download a Parquet artifact from the bronze zone."""
    obj = _client().get_object(Bucket=_bucket(), Key=key)
    return pd.read_parquet(io.BytesIO(obj["Body"].read()))


def read_bytes(key: str) -> bytes:
    """Download raw bytes from the bronze zone."""
    obj = _client().get_object(Bucket=_bucket(), Key=key)
    return obj["Body"].read()

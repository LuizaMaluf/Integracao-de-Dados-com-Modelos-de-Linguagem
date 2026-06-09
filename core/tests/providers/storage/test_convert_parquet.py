import io
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from core.providers.storage.minio import MinIOProvider


def _provider():
    return MinIOProvider({
        "endpoint_env": "MINIO_ENDPOINT",
        "access_key_env": "MINIO_ACCESS_KEY",
        "secret_key_env": "MINIO_SECRET_KEY",
        "bucket_env": "MINIO_BUCKET",
    })


def test_convert_to_parquet_returns_correct_key(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET", "raw")

    provider = _provider()
    original_key = "raw/bacen_sgs/20704/original/2026-06-09.json"
    raw_json = pd.DataFrame([{"data": "01/06/2026", "valor": "1234.56"}]).to_json(orient="records")

    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": io.BytesIO(raw_json.encode())}
    mock_client.create_bucket.return_value = None
    mock_client.put_object.return_value = None
    mock_client.exceptions.ClientError = Exception

    with patch.object(provider, "_client", return_value=mock_client):
        result = provider.convert_to_parquet(original_key)

    today = date.today().isoformat()
    assert result == f"processed/staging/bacen_sgs/20704/{today}.parquet"


def test_write_raw_accepts_str(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET", "raw")

    provider = _provider()
    mock_client = MagicMock()
    mock_client.create_bucket.return_value = None
    mock_client.put_object.return_value = None
    mock_client.exceptions.ClientError = Exception

    with patch.object(provider, "_client", return_value=mock_client):
        key = provider.write_raw('[{"x": 1}]', "src", "code", "json")

    body = mock_client.put_object.call_args[1]["Body"]
    assert isinstance(body, bytes)
    assert key.endswith(".json")

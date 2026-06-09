import json
from unittest.mock import MagicMock, patch

from extractors.api_extractor import ApiExtractor


def _mock_http(records: list) -> MagicMock:
    response = MagicMock()
    response.json.return_value = records
    response.raise_for_status.return_value = None
    client = MagicMock()
    client.get.return_value = response
    return client


def test_extract_raw_builds_series_url():
    cfg = {
        "source_name": "bacen_sgs",
        "type": "api_series",
        "base_url": "https://api.bcb.gov.br/dados/serie",
        "auth_strategy": "none",
        "pagination_strategy": "none",
        "ultimos": 13,
        "params": {"formato": "json"},
        "serie": {"codigo": 20704, "tabela": "financiamentos_pf_total"},
    }
    records = [{"data": "01/06/2026", "valor": "1234.56"}]
    mock_client = _mock_http(records)

    with patch("httpx.Client") as cls:
        cls.return_value.__enter__.return_value = mock_client
        result = ApiExtractor(cfg).extract_raw()

    assert json.loads(result) == records
    called_url = mock_client.get.call_args[0][0]
    assert "bcdata.sgs.20704" in called_url
    assert "ultimos/13" in called_url


def test_extract_raw_uses_url_directly_when_no_serie():
    cfg = {
        "source_name": "test_api",
        "type": "api",
        "url": "https://example.com/data",
        "auth_strategy": "none",
        "pagination_strategy": "none",
        "params": {},
    }
    records = [{"id": 1}]
    mock_client = _mock_http(records)

    with patch("httpx.Client") as cls:
        cls.return_value.__enter__.return_value = mock_client
        result = ApiExtractor(cfg).extract_raw()

    assert json.loads(result) == records
    assert mock_client.get.call_args[0][0] == "https://example.com/data"


def test_get_extractor_returns_api_extractor_for_api_series():
    from extractors import get_extractor
    cfg = {"type": "api_series", "source_name": "test", "base_url": "http://x"}
    extractor = get_extractor(cfg)
    assert isinstance(extractor, ApiExtractor)

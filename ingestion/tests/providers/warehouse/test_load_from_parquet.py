from unittest.mock import MagicMock, patch

import pandas as pd

from providers.warehouse.postgres import PostgreSQLProvider


def test_load_from_parquet_delegates_to_load():
    provider = PostgreSQLProvider({"conn_env": "DW_CONN"})
    df = pd.DataFrame([{"data": "2026-06-01", "valor": 1234.56}])
    parquet_key = "processed/staging/bacen_sgs/20704/2026-06-09.parquet"

    mock_storage = MagicMock()
    mock_storage.read_parquet.return_value = df

    with patch("providers.get_storage", return_value=mock_storage), \
         patch.object(provider, "load") as mock_load:
        provider.load_from_parquet(parquet_key, "bacen_sgs", "financiamentos_pf_total")

    mock_storage.read_parquet.assert_called_once_with(parquet_key)
    mock_load.assert_called_once()
    args = mock_load.call_args[0]
    assert args[1] == "bacen_sgs"
    assert args[2] == "financiamentos_pf_total"

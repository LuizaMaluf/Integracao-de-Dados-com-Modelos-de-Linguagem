from unittest.mock import MagicMock, patch

import pandas as pd

from core.providers.warehouse.postgres import PostgreSQLProvider


def test_load_parquet_delegates_to_load_df():
    provider = PostgreSQLProvider({"conn_env": "DW_CONN"})
    df = pd.DataFrame([{"data": "2026-06-01", "valor": 1234.56}])
    parquet_key = "processed/staging/bacen_sgs/20704/2026-06-09.parquet"

    mock_storage = MagicMock()
    mock_storage.read_parquet.return_value = df

    with patch("core.providers.factory.get_storage", return_value=mock_storage), \
         patch.object(provider, "load_df") as mock_load_df:
        provider.load_parquet(parquet_key, "bacen_sgs", "financiamentos_pf_total")

    mock_storage.read_parquet.assert_called_once_with(parquet_key)
    mock_load_df.assert_called_once()
    args = mock_load_df.call_args[0]
    assert args[1] == "bacen_sgs"
    assert args[2] == "financiamentos_pf_total"

"""
BigQueryProvider: loads data into Google BigQuery.
Config keys: project_env, dataset
Credentials resolved via Application Default Credentials (ADC).

Not yet implemented — stub for future use.
"""
import pandas as pd

from core.providers.warehouse.base import WarehouseProvider


class BigQueryProvider(WarehouseProvider):
    def load_df(self, df: pd.DataFrame, schema: str, table: str) -> None:
        raise NotImplementedError(
            "BigQueryProvider is not yet implemented. "
            "Install google-cloud-bigquery and implement this method."
        )

    def load_parquet(self, parquet_key: str, schema: str, table: str) -> None:
        raise NotImplementedError(
            "BigQueryProvider is not yet implemented. "
            "Install google-cloud-bigquery and implement this method."
        )

"""
BigQueryProvider: loads data into Google BigQuery.
Config keys: project_env, dataset
Credentials resolved via Application Default Credentials (ADC).

Not yet implemented — stub for future use.
"""
import pandas as pd

from .base import WarehouseProvider


class BigQueryProvider(WarehouseProvider):
    def load(self, df: pd.DataFrame, schema: str, table: str) -> None:
        raise NotImplementedError(
            "BigQueryProvider is not yet implemented. "
            "Install google-cloud-bigquery and implement this method."
        )

    def load_from_parquet(self, parquet_key: str, schema: str, table: str) -> None:
        raise NotImplementedError(
            "BigQueryProvider is not yet implemented. "
            "Install google-cloud-bigquery and implement this method."
        )

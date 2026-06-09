"""
DatabricksProvider: loads data into Databricks.
Config keys: project_env, dataset
Credentials resolver via Application Default Credentials (ADC).

Not yet implemented - stub for future use (MGI)
"""

import pandas as pd
from core.providers.warehouse.base import WarehouseProvider

class DatabricksProvider(WarehouseProvider):
    def load_df(self, df: pd.DataFrame, schema: str, table: str) -> None:
        raise NotImplementedError(
            "DatabricksProvider is not yet implemented. "
        )

    def load_parquet(self, parquet_key: str, schema: str, table: str) -> None: 
        raise NotImplementedError(
            "DatabricksProvider is not yet implemented. "
        )
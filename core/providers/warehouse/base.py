"""
WarehouseProvider: abstract contract for the data warehouse (bronze zone).
Concrete implementations: PostgreSQLProvider, BigQueryProvider, ...
"""
from abc import ABC, abstractmethod

import pandas as pd


class WarehouseProvider(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def load(self, df: pd.DataFrame, schema: str, table: str) -> None:
        """Load a DataFrame into the warehouse at schema.table."""
        ...

    @abstractmethod
    def load_from_parquet(self, parquet_key: str, schema: str, table: str) -> None:
        """Read Parquet from storage and load into the warehouse."""
        ...

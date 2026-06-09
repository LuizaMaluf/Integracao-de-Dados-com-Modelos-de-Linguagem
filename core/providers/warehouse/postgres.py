"""
PostgreSQLProvider: loads data into PostgreSQL via DuckDB transformation adapter.
Config keys: conn_env
DuckDB normalizes column names (snake_case) and adds _loaded_at before writing.
"""
import os
import re

import duckdb
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from core.providers.warehouse.base import WarehouseProvider


class PostgreSQLProvider(WarehouseProvider):
    def _engine(self):
        return create_engine(os.environ[self.config["conn_env"]])

    def _ensure_schema(self, schema: str) -> None:
        try:
            with self._engine().begin() as conn:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        except IntegrityError:
            pass

    @staticmethod
    def _normalize_col(name: str) -> str:
        return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())

    def load_df(self, df: pd.DataFrame, schema: str, table: str) -> None:
        self._ensure_schema(schema)

        with duckdb.connect() as conn:
            conn.register("raw", df)
            col_exprs = ", ".join(
                f'"{col}" AS {self._normalize_col(col)}' for col in df.columns
            )
            normalized: pd.DataFrame = conn.execute(f"""
                SELECT {col_exprs}, current_timestamp AS _loaded_at
                FROM raw
            """).df()

        normalized.to_sql(table, self._engine(), schema=schema, if_exists="replace", index=False)

    def load_parquet(self, parquet_key: str, schema: str, table: str) -> None:
        from core.providers.factory import get_storage
        df = get_storage().read_parquet(parquet_key)
        self.load_df(df, schema, table)

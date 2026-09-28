"""
Silver Zone: cleaned, queryable staging tables in DuckDB.
Normalizes column names and builds TableMetadata for the Integration Agent.
"""
import os
from datetime import date

import duckdb
import pandas as pd
from govhub.ingestion.registry import normalize_name
from govhub.integration.loaders.base import TableMetadata


def _conn() -> duckdb.DuckDBPyConnection:
    path = os.environ.get("DUCKDB_PATH", "/opt/airflow/data/silver.duckdb")
    return duckdb.connect(path)


def write(df: pd.DataFrame, source_name: str) -> str:
    """Write a normalized DataFrame to DuckDB silver zone. Returns the table name."""
    df = df.copy()
    df.columns = [normalize_name(c) for c in df.columns]

    table_name = f"{normalize_name(source_name)}_{date.today().strftime('%Y%m%d')}"
    with _conn() as conn:
        conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
    return table_name


def read(table_name: str) -> pd.DataFrame:
    """Load a silver table as a DataFrame."""
    with _conn() as conn:
        return conn.execute(f"SELECT * FROM {table_name}").df()


def list_tables() -> list[str]:
    """Return all table names currently in the silver zone."""
    with _conn() as conn:
        rows = conn.execute("SHOW TABLES").fetchall()
    return [r[0] for r in rows]


def build_metadata(df: pd.DataFrame, table_name: str) -> TableMetadata:
    """Build a TableMetadata object compatible with IntegrationAgent."""
    return TableMetadata.from_dataframe(df, table_name)

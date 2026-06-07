"""
Silver Zone: cleaned, queryable staging tables in DuckDB.
Normalizes column names and builds TableMetadata for the Integration Agent.
"""
import os
import re
import sys
from datetime import date

import duckdb
import pandas as pd

# Allow importing fase01/src from inside the container
sys.path.insert(0, "/opt/airflow/agent_src")
from loaders.base import TableMetadata  # noqa: E402


def _conn() -> duckdb.DuckDBPyConnection:
    path = os.environ.get("DUCKDB_PATH", "/opt/airflow/data/silver.duckdb")
    return duckdb.connect(path)


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


def write(df: pd.DataFrame, source_name: str) -> str:
    """Write a normalized DataFrame to DuckDB silver zone. Returns the table name."""
    df = df.copy()
    df.columns = [_normalize_name(c) for c in df.columns]

    table_name = f"{_normalize_name(source_name)}_{date.today().strftime('%Y%m%d')}"
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
    return TableMetadata(
        name=table_name,
        columns=list(df.columns),
        dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
        row_count=len(df),
        sample=df.head(5).to_dict(orient="records"),
    )

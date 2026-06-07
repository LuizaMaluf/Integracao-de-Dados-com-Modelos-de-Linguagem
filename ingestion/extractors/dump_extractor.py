"""
Extracts data from database dumps (SQL or compressed CSV).
Config keys: format, file_path, tables, encoding, separator.
"""
import gzip
from io import StringIO
from pathlib import Path

import pandas as pd

from .base import BaseExtractor


class DumpExtractor(BaseExtractor):
    """Parses a SQL or CSV.GZ dump and returns one DataFrame per declared table."""

    def extract(self) -> dict[str, pd.DataFrame]:
        """Returns {table_name: DataFrame} instead of a single DataFrame."""
        fmt = self.config.get("format", "csv_gz")
        if fmt == "csv_gz":
            return self._extract_csv_gz()
        if fmt == "sql":
            return self._extract_sql()
        raise ValueError(f"Unsupported dump format: {fmt}")

    def _extract_csv_gz(self) -> dict[str, pd.DataFrame]:
        file_path = self.config["file_path"]
        with gzip.open(file_path, "rt", encoding=self.config.get("encoding", "utf-8")) as f:
            df = pd.read_csv(f, sep=self.config.get("separator", ","))
        df = self._select_columns(df)
        return {self.source_name: df}

    def _extract_sql(self) -> dict[str, pd.DataFrame]:
        from sqlalchemy import create_engine, text

        sql_path = Path(self.config["file_path"])
        # Load dump into an in-memory SQLite DB then read each declared table
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text(sql_path.read_text(encoding=self.config.get("encoding", "utf-8"))))

        tables = self.config.get("tables") or []
        result = {}
        with engine.connect() as conn:
            if not tables:
                from sqlalchemy import inspect
                tables = inspect(engine).get_table_names()
            for table in tables:
                result[table] = pd.read_sql_table(table, conn)
        return result

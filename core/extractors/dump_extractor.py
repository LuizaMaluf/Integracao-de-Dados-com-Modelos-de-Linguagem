"""
Extracts data from database dumps (SQL or compressed CSV).
Config keys: format, file_path, tables, encoding, separator.
"""
import gzip
from io import StringIO
from pathlib import Path

import pandas as pd

from core.extractors.base import BaseExtractor

class DumpExtractor(BaseExtractor):
    """Parses a SQL or CSV.GZ dump and returns one DataFrame per declared table."""

    def extract(self) -> dict[str, pd.DataFrame]:
        ...

    def _extract_csv_gz(self) -> dict[str, pd.DataFrame]:
        ...

    def _extract_sql(self) -> dict[str, pd.DataFrame]:
        ...
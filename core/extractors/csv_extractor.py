"""
Extracts data from CSV or XLSX files.
Config keys used: file_path, columns, skip_rows, encoding, separator, sheet_name, type.
"""
import pandas as pd

from core.extractors.base import BaseExtractor


class CsvExtractor(BaseExtractor):
    """Reads a CSV or XLSX file applying column and row selection from Source Config."""

    def extract(self) -> pd.DataFrame:
        ...

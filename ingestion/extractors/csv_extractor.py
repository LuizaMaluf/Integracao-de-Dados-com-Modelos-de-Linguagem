"""
Extracts data from CSV or XLSX files.
Config keys used: file_path, columns, skip_rows, encoding, separator, sheet_name, type.
"""
import pandas as pd

from .base import BaseExtractor


class CsvExtractor(BaseExtractor):
    """Reads a CSV or XLSX file applying column and row selection from Source Config."""

    def extract(self) -> pd.DataFrame:
        file_path = self.config["file_path"]
        source_type = self.config.get("type", "csv")

        if source_type == "xlsx":
            df = pd.read_excel(
                file_path,
                sheet_name=self.config.get("sheet_name", 0),
                skiprows=self.config.get("skip_rows", 0),
            )
        else:
            df = pd.read_csv(
                file_path,
                sep=self.config.get("separator", ","),
                encoding=self.config.get("encoding", "utf-8"),
                skiprows=self.config.get("skip_rows", 0),
            )

        return self._select_columns(df)

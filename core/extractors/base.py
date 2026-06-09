"""
Base extractor contract. Every source-type extractor inherits from this.
"""
from abc import ABC

import pandas as pd


class BaseExtractor(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.source_name: str = config["source_name"]

    def extract_raw(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} does not implement extract_raw()")

    def extract(self) -> pd.DataFrame:
        return pd.read_json(self.extract_raw(), orient="records")

    def _select_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = self.config.get("columns")
        if cols:
            existing = [c for c in cols if c in df.columns]
            df = df[existing]
        return df

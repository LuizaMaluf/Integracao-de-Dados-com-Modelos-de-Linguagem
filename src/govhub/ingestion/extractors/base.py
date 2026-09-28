"""
Base extractor contract. Every source-type extractor inherits from this.
"""
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


class BaseExtractor(ABC):
    """Reads a source according to its config and returns a raw DataFrame."""

    def __init__(self, config: dict):
        self.config = config
        self.source_name: str = config["source_name"]

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Pull data from the source and return it as a raw DataFrame."""
        ...

    def _select_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply column selection from config if declared."""
        cols = self.config.get("columns")
        if cols:
            existing = [c for c in cols if c in df.columns]
            df = df[existing]
        return df

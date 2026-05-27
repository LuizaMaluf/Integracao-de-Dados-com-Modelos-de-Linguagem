"""
Value normalization utilities for cross-table matching.
"""
import re
import pandas as pd


def normalize_series(series: pd.Series) -> pd.Series:
    """Applies standard normalization: strip, uppercase, remove special chars."""
    if series.dtype == object or str(series.dtype) == "string":
        return (
            series.astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"[.\-/\s]", "", regex=True)
        )
    return series.astype(str).str.strip()


def pad_left(series: pd.Series, width: int, fillchar: str = "0") -> pd.Series:
    return series.astype(str).str.strip().str.zfill(width)


def remove_leading_zeros(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lstrip("0")


def extract_digits(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\D", "", regex=True)


def concat_columns(df: pd.DataFrame, cols: list[str], sep: str = "") -> pd.Series:
    return df[cols].astype(str).apply(lambda row: sep.join(row.values), axis=1)

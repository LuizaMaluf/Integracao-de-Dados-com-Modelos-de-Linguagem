"""
Structural analyzer: dtype compatibility, cardinality, uniqueness, null rate.
"""
import pandas as pd
from dataclasses import dataclass


DTYPE_COMPAT: dict[str, set[str]] = {
    "object": {"object", "category"},
    "int64": {"int64", "int32", "float64", "object"},
    "float64": {"float64", "int64", "object"},
    "category": {"category", "object"},
}


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    unique_count: int
    null_rate: float
    uniqueness_rate: float
    top_values: list


def profile_column(series: pd.Series) -> ColumnProfile:
    n = len(series)
    non_null = series.dropna()
    return ColumnProfile(
        name=series.name,
        dtype=str(series.dtype),
        unique_count=non_null.nunique(),
        null_rate=1 - len(non_null) / n if n > 0 else 1.0,
        uniqueness_rate=non_null.nunique() / len(non_null) if len(non_null) > 0 else 0.0,
        top_values=non_null.value_counts().head(5).index.tolist(),
    )


def dtype_compatible(dtype_a: str, dtype_b: str) -> bool:
    compat = DTYPE_COMPAT.get(dtype_a, {dtype_a})
    return dtype_b in compat


def cardinality_label(uniqueness_rate: float) -> str:
    if uniqueness_rate > 0.95:
        return "high (near-unique)"
    if uniqueness_rate > 0.5:
        return "medium"
    return "low (repetitive)"

"""
Statistical analyzer: value overlap, match rate between column pairs.
"""
import pandas as pd
from src.transformers.normalizer import normalize_series


def match_rate(
    series_a: pd.Series,
    series_b: pd.Series,
    normalize: bool = True,
) -> float:
    """Fraction of values in series_a that exist in series_b."""
    if normalize:
        series_a = normalize_series(series_a)
        series_b = normalize_series(series_b)

    set_b = set(series_b.dropna().unique())
    values_a = series_a.dropna()

    if len(values_a) == 0:
        return 0.0

    hits = values_a.isin(set_b).sum()
    return hits / len(values_a)


def overlap_stats(
    series_a: pd.Series,
    series_b: pd.Series,
    normalize: bool = True,
) -> dict:
    if normalize:
        series_a = normalize_series(series_a)
        series_b = normalize_series(series_b)

    set_a = set(series_a.dropna().unique())
    set_b = set(series_b.dropna().unique())
    intersection = set_a & set_b

    return {
        "unique_a": len(set_a),
        "unique_b": len(set_b),
        "intersection": len(intersection),
        "match_rate_a_in_b": len(intersection) / len(set_a) if set_a else 0.0,
        "match_rate_b_in_a": len(intersection) / len(set_b) if set_b else 0.0,
        "sample_matches": list(intersection)[:5],
    }

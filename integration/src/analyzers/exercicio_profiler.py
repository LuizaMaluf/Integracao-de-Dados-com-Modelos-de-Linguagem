"""
Detects exercício (fiscal year) columns and computes their value distribution.
"""
from __future__ import annotations

import re

import pandas as pd

_YEAR_RE = re.compile(r"^\d{4}$")
_YEAR_MIN = 1990
_YEAR_MAX = 2040
_MATCH_THRESHOLD = 0.80


def detect_exercicio_column(
    df: pd.DataFrame,
    domain_groups: dict[str, list[str]] | None = None,
) -> str | None:
    """Return the name of the exercício column in df, or None if not found.

    Checks by domain group alias first; falls back to regex coverage.
    """
    if domain_groups:
        aliases = {a.lower() for a in domain_groups.get("exercicio", [])}
        for col in df.columns:
            normalized = re.sub(r"[^a-z0-9]", "_", col.lower().strip())
            if normalized in aliases:
                return col

    for col in df.columns:
        series = df[col].dropna().astype(str)
        if len(series) == 0:
            continue
        matches = series.str.match(r"^\d{4}$")
        if matches.sum() / len(series) < _MATCH_THRESHOLD:
            continue
        try:
            years = series[matches].astype(int)
            if years.between(_YEAR_MIN, _YEAR_MAX).all():
                return col
        except (ValueError, TypeError):
            pass

    return None


def exercicio_distribution(
    df: pd.DataFrame,
    domain_groups: dict[str, list[str]] | None = None,
) -> dict[str, int] | None:
    """Return {year_str: count} for the exercício column, or None if absent."""
    col = detect_exercicio_column(df, domain_groups)
    if col is None:
        return None
    raw = df[col].dropna().astype(str).value_counts().to_dict()
    return {k: int(v) for k, v in raw.items() if _YEAR_RE.match(k)}

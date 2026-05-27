"""
Detects value patterns in a series and maps them to known domain patterns.
"""
import re
import pandas as pd
from src.config.domain import DOMAIN_KEY_PATTERNS


def detect_pattern(series: pd.Series, sample_size: int = 200) -> dict:
    sample = series.dropna().astype(str).head(sample_size)

    results = {}
    for domain, pattern in DOMAIN_KEY_PATTERNS.items():
        matches = sample.str.match(pattern).sum()
        results[domain] = matches / len(sample) if len(sample) > 0 else 0.0

    best = max(results, key=results.get) if results else None
    best_score = results.get(best, 0.0) if best else 0.0

    return {
        "best_domain_match": best if best_score > 0.5 else None,
        "best_score": best_score,
        "all_scores": results,
        "avg_length": sample.str.len().mean(),
        "sample_values": sample.head(5).tolist(),
    }


def patterns_compatible(pattern_a: dict, pattern_b: dict) -> bool:
    d_a = pattern_a.get("best_domain_match")
    d_b = pattern_b.get("best_domain_match")
    if d_a and d_b:
        return d_a == d_b
    len_a = pattern_a.get("avg_length", 0)
    len_b = pattern_b.get("avg_length", 0)
    return abs(len_a - len_b) <= 2

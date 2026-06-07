"""
Content Evidence Layer: content-based compatibility signals for a column pair.
Produces ContentEvidence without using column name similarity as a signal.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.analyzers.statistical import overlap_stats
from src.transformers.pattern_detector import detect_pattern

SAMPLE_SIZE = 100
PROMOTION_THRESHOLD = 0.50


@dataclass
class ContentEvidence:
    format_match: bool
    format_a: str | None
    format_b: str | None
    overlap_rate: float
    substring_match_rate: float
    content_score: float

    def promoted(self, threshold: float = PROMOTION_THRESHOLD) -> bool:
        return self.content_score >= threshold

    def to_dict(self) -> dict:
        return {
            "format_match": self.format_match,
            "format_a": self.format_a,
            "format_b": self.format_b,
            "overlap_rate": self.overlap_rate,
            "substring_match_rate": self.substring_match_rate,
            "content_score": self.content_score,
        }


def _sample_nonnull(series: pd.Series, n: int = SAMPLE_SIZE) -> pd.Series:
    return series.dropna().head(n)


def _substring_match_rate(sample_a: pd.Series, sample_b: pd.Series) -> float:
    """Max of: fraction of a-values that appear as substring in any b-value, and vice versa."""
    if len(sample_a) == 0 or len(sample_b) == 0:
        return 0.0

    str_a = sample_a.astype(str).tolist()
    str_b = sample_b.astype(str).tolist()
    set_b = set(str_b)
    set_a = set(str_a)

    hits_ab = sum(1 for v in str_a if any(v in bv for bv in set_b)) / len(str_a)
    hits_ba = sum(1 for v in str_b if any(v in av for av in set_a)) / len(str_b)

    return round(max(hits_ab, hits_ba), 4)


def analyze(series_a: pd.Series, series_b: pd.Series) -> ContentEvidence:
    """Compute ContentEvidence for a column pair using content-only signals."""
    sample_a = _sample_nonnull(series_a)
    sample_b = _sample_nonnull(series_b)

    pat_a = detect_pattern(sample_a)
    pat_b = detect_pattern(sample_b)
    fmt_a: str | None = pat_a.get("best_domain_match")
    fmt_b: str | None = pat_b.get("best_domain_match")
    format_match = bool(fmt_a and fmt_b and fmt_a == fmt_b)

    stats = overlap_stats(sample_a, sample_b, normalize=True)
    overlap_rate = round(stats["match_rate_a_in_b"], 4)

    smr = _substring_match_rate(sample_a, sample_b)

    if format_match:
        content_score = round(max(overlap_rate, smr), 4)
    else:
        # Second term ensures strong substring signal (Derived Key) can independently promote.
        # smr >= 0.625 → second term >= 0.50, reaching the promotion threshold on its own.
        content_score = round(max(0.6 * overlap_rate + 0.4 * smr, smr * 0.8), 4)

    return ContentEvidence(
        format_match=format_match,
        format_a=fmt_a,
        format_b=fmt_b,
        overlap_rate=overlap_rate,
        substring_match_rate=smr,
        content_score=content_score,
    )

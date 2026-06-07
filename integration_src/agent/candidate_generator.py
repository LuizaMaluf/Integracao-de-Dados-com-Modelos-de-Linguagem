"""
Generates candidate key pairs from two tables using semantic and structural signals.
"""
from dataclasses import dataclass, field
from itertools import product

import pandas as pd

from src.analyzers.semantic import semantic_score, find_domain_group
from src.analyzers.structural import profile_column, dtype_compatible, cardinality_label
from src.analyzers.statistical import overlap_stats
from src.transformers.pattern_detector import detect_pattern, patterns_compatible
from src.loaders.base import TableMetadata


@dataclass
class CandidateKey:
    columns_a: list[str]
    columns_b: list[str]
    semantic_score: float = 0.0
    structural_score: float = 0.0
    match_rate: float = 0.0
    cardinality: str = ""
    pattern_a: dict = field(default_factory=dict)
    pattern_b: dict = field(default_factory=dict)
    overlap: dict = field(default_factory=dict)
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    required_transformations: list[str] = field(default_factory=list)
    # None = discovered via semantic path; float = discovered via Content Evidence Layer
    content_score: float | None = None

    @property
    def score(self) -> float:
        return round(
            0.35 * self.semantic_score
            + 0.30 * self.match_rate
            + 0.20 * self.structural_score
            + 0.15 * (1.0 if self.pattern_a.get("best_domain_match") else 0.0),
            4,
        )


class CandidateGenerator:
    def __init__(
        self,
        df_a: pd.DataFrame,
        meta_a: TableMetadata,
        df_b: pd.DataFrame,
        meta_b: TableMetadata,
        semantic_threshold: float = 0.3,
        max_candidates: int = 10,
    ):
        self.df_a = df_a
        self.meta_a = meta_a
        self.df_b = df_b
        self.meta_b = meta_b
        self.semantic_threshold = semantic_threshold
        self.max_candidates = max_candidates

    def generate(self) -> list[CandidateKey]:
        candidates: list[CandidateKey] = []

        for col_a, col_b in product(self.meta_a.columns, self.meta_b.columns):
            sem = semantic_score(col_a, col_b)
            if sem < self.semantic_threshold:
                continue

            dtype_a = self.meta_a.dtypes.get(col_a, "object")
            dtype_b = self.meta_b.dtypes.get(col_b, "object")
            struct = 1.0 if dtype_compatible(dtype_a, dtype_b) else 0.0

            profile_a = profile_column(self.df_a[col_a])
            profile_b = profile_column(self.df_b[col_b])

            pattern_a = detect_pattern(self.df_a[col_a])
            pattern_b = detect_pattern(self.df_b[col_b])

            overlap = overlap_stats(self.df_a[col_a], self.df_b[col_b])
            mr = overlap["match_rate_a_in_b"]

            evidence_for, evidence_against, transforms = self._build_evidence(
                col_a, col_b, sem, struct, mr, profile_a, profile_b,
                pattern_a, pattern_b, dtype_a, dtype_b
            )

            candidate = CandidateKey(
                columns_a=[col_a],
                columns_b=[col_b],
                semantic_score=sem,
                structural_score=struct,
                match_rate=mr,
                cardinality=cardinality_label(max(profile_a.uniqueness_rate, profile_b.uniqueness_rate)),
                pattern_a=pattern_a,
                pattern_b=pattern_b,
                overlap=overlap,
                evidence_for=evidence_for,
                evidence_against=evidence_against,
                required_transformations=transforms,
            )
            candidates.append(candidate)

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[: self.max_candidates]

    def _build_evidence(
        self, col_a, col_b, sem, struct, mr,
        profile_a, profile_b, pattern_a, pattern_b, dtype_a, dtype_b
    ) -> tuple[list, list, list]:
        evidence_for = []
        evidence_against = []
        transforms = []

        if sem >= 0.8:
            evidence_for.append(f"High name similarity ({sem:.2f}): '{col_a}' ~ '{col_b}'")
        elif sem >= 0.5:
            evidence_for.append(f"Moderate name similarity ({sem:.2f})")

        group_a = find_domain_group(col_a)
        group_b = find_domain_group(col_b)
        if group_a and group_a == group_b:
            evidence_for.append(f"Both columns belong to domain group '{group_a}'")

        if mr >= 0.8:
            evidence_for.append(f"High match rate: {mr:.1%} of values in A found in B")
        elif mr >= 0.5:
            evidence_for.append(f"Moderate match rate: {mr:.1%}")
        else:
            evidence_against.append(f"Low match rate: {mr:.1%}")

        if struct == 0.0:
            evidence_against.append(f"Incompatible dtypes: {dtype_a} vs {dtype_b}")
            transforms.append(f"Cast {col_b} ({dtype_b}) to {dtype_a} before join")

        if profile_a.null_rate > 0.2:
            evidence_against.append(f"High null rate in {col_a}: {profile_a.null_rate:.1%}")
        if profile_b.null_rate > 0.2:
            evidence_against.append(f"High null rate in {col_b}: {profile_b.null_rate:.1%}")

        pd_a = pattern_a.get("best_domain_match")
        pd_b = pattern_b.get("best_domain_match")
        if pd_a and pd_b and pd_a == pd_b:
            evidence_for.append(f"Both match domain pattern '{pd_a}'")
        elif pd_a and pd_b and pd_a != pd_b:
            evidence_against.append(f"Pattern mismatch: '{pd_a}' vs '{pd_b}'")

        len_a = pattern_a.get("avg_length", 0)
        len_b = pattern_b.get("avg_length", 0)
        if abs(len_a - len_b) > 3:
            evidence_against.append(f"Avg value length differs: {len_a:.1f} vs {len_b:.1f}")
            transforms.append("Check if padding (zfill) or trimming is needed")

        return evidence_for, evidence_against, transforms

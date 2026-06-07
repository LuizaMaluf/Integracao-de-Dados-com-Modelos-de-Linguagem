"""
Validates a DomainContext against the columns of two input tables.
Reports Context Coverage and lists unrecognized columns.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.config.context_loader import DomainContext


COVERAGE_WARNING_THRESHOLD = 0.60


@dataclass
class ValidationResult:
    domain_name: str
    is_default: bool
    total_columns: int
    recognized_columns: list[str]
    unrecognized_columns: list[str]
    coverage: float
    passes_threshold: bool
    warning: str | None


def validate_context(
    context: DomainContext,
    columns_a: list[str],
    columns_b: list[str],
    threshold: float = COVERAGE_WARNING_THRESHOLD,
) -> ValidationResult:
    all_columns = list(columns_a) + list(columns_b)
    recognized = [col for col in all_columns if _find_group(col, context.semantic_groups)]
    unrecognized = [col for col in all_columns if col not in recognized]
    coverage = len(recognized) / len(all_columns) if all_columns else 1.0
    passes = coverage >= threshold

    warning = None
    if not passes:
        warning = (
            f"Context coverage is {coverage:.0%} ({len(recognized)}/{len(all_columns)} columns recognized). "
            f"Below the recommended threshold of {threshold:.0%}. "
            f"Consider running `definir-contexto` to update the Domain Context."
        )

    return ValidationResult(
        domain_name=context.domain_name,
        is_default=context.is_default,
        total_columns=len(all_columns),
        recognized_columns=recognized,
        unrecognized_columns=unrecognized,
        coverage=coverage,
        passes_threshold=passes,
        warning=warning,
    )


def _normalize(name: str) -> str:
    name = name.lower().strip()
    return re.sub(r"[^a-z0-9]", "_", name)


def _find_group(col_name: str, semantic_groups: dict[str, list[str]]) -> str | None:
    normalized = _normalize(col_name)
    for group, aliases in semantic_groups.items():
        for alias in aliases:
            if _normalize(alias) == normalized:
                return group
    for group, aliases in semantic_groups.items():
        for alias in aliases:
            norm_alias = _normalize(alias)
            if norm_alias in normalized or normalized in norm_alias:
                return group
    return None

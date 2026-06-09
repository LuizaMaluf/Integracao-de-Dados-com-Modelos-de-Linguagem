"""
Semantic analyzer: column name similarity and domain group matching.
"""
import re
from difflib import SequenceMatcher
from src.config.domain import DOMAIN_SEMANTIC_GROUPS


def normalize_col_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def name_similarity(col_a: str, col_b: str) -> float:
    a = normalize_col_name(col_a)
    b = normalize_col_name(col_b)
    return SequenceMatcher(None, a, b).ratio()


def find_domain_group(col_name: str, store=None) -> str | None:
    normalized = normalize_col_name(col_name)

    # Build merged groups: start with builtin, overlay store entries on top
    merged_groups: dict = dict(DOMAIN_SEMANTIC_GROUPS)
    if store is not None:
        for ctx in store.get_domain_contexts():
            for group, aliases in ctx.get("semantic_groups", {}).items():
                merged_groups[group] = aliases

    for group, aliases in merged_groups.items():
        for alias in aliases:
            if normalize_col_name(alias) == normalized:
                return group
    # partial match fallback
    for group, aliases in merged_groups.items():
        for alias in aliases:
            if normalize_col_name(alias) in normalized or normalized in normalize_col_name(alias):
                return group
    return None


def semantic_score(col_a: str, col_b: str) -> float:
    """Returns 0.0–1.0 based on name similarity and shared domain group."""
    sim = name_similarity(col_a, col_b)
    group_a = find_domain_group(col_a)
    group_b = find_domain_group(col_b)

    if group_a and group_b and group_a == group_b:
        return max(sim, 0.75)
    return sim

"""
Loads a Domain Context JSON and exposes semantic groups and key patterns.
Falls back to the built-in orçamentário federal defaults when no context is provided.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.config.domain import DOMAIN_SEMANTIC_GROUPS, DOMAIN_KEY_PATTERNS


class DomainContext:
    def __init__(
        self,
        domain_name: str,
        semantic_groups: dict[str, list[str]],
        key_patterns: dict[str, str],
        source_path: Path | None = None,
    ):
        self.domain_name = domain_name
        self.semantic_groups = semantic_groups
        self.key_patterns = key_patterns
        self.source_path = source_path
        self.is_default = source_path is None

    def __repr__(self) -> str:
        return f"DomainContext(domain='{self.domain_name}', groups={len(self.semantic_groups)}, default={self.is_default})"


def load_context(path: str | Path | None) -> DomainContext:
    """
    Load a Domain Context from a JSON file.
    If path is None or missing, returns the built-in orçamentário federal defaults.
    """
    if path is None:
        return _default_context()

    path = Path(path)
    if not path.exists():
        return _default_context()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _validate_schema(data, path)
        return DomainContext(
            domain_name=data["domain_name"],
            semantic_groups=data["semantic_groups"],
            key_patterns=data.get("key_patterns", {}),
            source_path=path,
        )
    except (json.JSONDecodeError, KeyError) as exc:
        raise ValueError(f"Invalid Domain Context file at '{path}': {exc}") from exc


def _default_context() -> DomainContext:
    return DomainContext(
        domain_name="orcamento_federal_brasileiro",
        semantic_groups=DOMAIN_SEMANTIC_GROUPS,
        key_patterns=DOMAIN_KEY_PATTERNS,
        source_path=None,
    )


def _validate_schema(data: dict, path: Path) -> None:
    required = {"domain_name", "semantic_groups"}
    missing = required - data.keys()
    if missing:
        raise KeyError(f"Missing required fields {missing} in '{path}'")
    if not isinstance(data["semantic_groups"], dict):
        raise KeyError("'semantic_groups' must be a dict")

"""
annotate_context — column-level domain annotation for the ingestion pipeline.

Called by the Airflow DAG as a @task after stage_silver.  The module is
intentionally free of Airflow imports so it can be unit-tested in isolation
and reused outside a DAG context.

Design decisions
----------------
- find_domain_group is called with `store=store` so that any domain_contexts
  stored in PostgreSQL by previous pipeline runs are taken into account,
  allowing the annotation to grow richer over time without code changes.
- annotate_table iterates every column exactly once and always calls
  upsert_column_annotation, even when domain_group is None, so the
  context.column_annotations table stays a complete record of every known
  column regardless of whether a group was detected.
- annotate_from_df is a thin convenience wrapper: it extracts column names
  from a pandas DataFrame and delegates to annotate_table, keeping the
  core logic in one place.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make integration/src importable when running from the ingestion tree
# (both in Airflow workers and in pytest).
_INTEGRATION_SRC = Path(__file__).parent.parent.parent / "integration"
if str(_INTEGRATION_SRC) not in sys.path:
    sys.path.insert(0, str(_INTEGRATION_SRC))

import pandas as pd
from src.analyzers.semantic import find_domain_group


def annotate_table(table_name: str, columns: list[str], store) -> None:
    """Annotate every column in *columns* with its domain group.

    Parameters
    ----------
    table_name:
        Fully-qualified Silver table name, e.g. ``"mir.empenhos"``.
    columns:
        Ordered list of column names as they appear in the table.
    store:
        A :class:`~src.store.context_store.ContextStore` instance (or
        compatible mock).  Passed to ``find_domain_group`` so that
        domain_contexts previously stored in PostgreSQL extend the built-in
        ``DOMAIN_SEMANTIC_GROUPS``.  When ``None``, the function returns
        immediately so callers in local development do not require a live DB.
    """
    if store is None:
        return
    for col in columns:
        group = find_domain_group(col, store=store)
        store.upsert_column_annotation(
            table_name,
            col,
            domain_group=group,
            semantic_tags=None,
        )


def annotate_from_df(table_name: str, df: pd.DataFrame, store) -> None:
    """Extract column names from *df* and call :func:`annotate_table`.

    Parameters
    ----------
    table_name:
        Fully-qualified Silver table name, e.g. ``"mir.empenhos"``.
    df:
        DataFrame whose columns are annotated.  Only ``df.columns`` is used;
        the row data is not inspected.
    store:
        A :class:`~src.store.context_store.ContextStore` instance (or
        compatible mock).
    """
    annotate_table(table_name, list(df.columns), store)

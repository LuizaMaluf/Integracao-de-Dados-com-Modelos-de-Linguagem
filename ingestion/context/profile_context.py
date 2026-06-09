"""
profile_context — basic DataFrame profiling for the ingestion pipeline.

Called by the Airflow DAG as a @task after stage_silver.  Free of Airflow
imports so it can be unit-tested in isolation.

Design decisions
----------------
- quality_ok uses a 20 % null-rate threshold, consistent with the integration
  pipeline's evidence-scoring approach: a table with many nulls is a weak
  evidence source.
- cardinality_per_col stores the number of distinct values per column, which
  the integration gateway can use to distinguish identifier columns
  (high cardinality) from categorical ones (low cardinality).
- exercicio_distribution is extracted only when a recognisable year/exercise
  column is found; otherwise it is stored as None to avoid bloating the
  profile for tables without a temporal dimension.
- store=None guard: the function returns immediately when no store is supplied
  so DAG tasks can call it safely during local development without a live DB.
"""
from __future__ import annotations

import pandas as pd


def profile_table(table_name: str, df: pd.DataFrame, store) -> None:
    """Calculate a basic profile of *df* and persist it in the ContextStore.

    Parameters
    ----------
    table_name:
        Fully-qualified Silver table name, e.g. ``"mir.empenhos"``.
    df:
        DataFrame to profile.
    store:
        A :class:`~src.store.context_store.ContextStore` instance (or
        compatible mock).  When ``None``, the function returns immediately
        so callers in local development do not require a live database.
    """
    if store is None:
        return

    row_count = len(df)

    # quality_ok = True se menos de 20 % das células são nulas
    total_cells = df.size or 1
    null_rate = df.isnull().sum().sum() / total_cells
    quality_ok = null_rate < 0.20

    # cardinalidade por coluna
    cardinality = {col: int(df[col].nunique()) for col in df.columns}

    # distribuição de exercício (se coluna existir)
    exercicio_col = next(
        (
            c
            for c in df.columns
            if "exercicio" in c.lower() or c.lower() in ("ano", "cd_ano")
        ),
        None,
    )
    exercicio_dist = None
    if exercicio_col:
        exercicio_dist = df[exercicio_col].astype(str).value_counts().to_dict()

    store.upsert_table_profile(
        table_name=table_name,
        row_count=row_count,
        exercicio_distribution=exercicio_dist,
        cardinality_per_col=cardinality,
        quality_ok=quality_ok,
    )

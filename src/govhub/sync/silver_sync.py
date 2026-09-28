"""
Costura A — Silver Sync: DuckDB → PostgreSQL.

Replica cada lote silver gravado no DuckDB (``<fonte>_YYYYMMDD``) para
``silver.<target_table>`` no PostgreSQL, ao fim de cada ingestão. Roda como task
do Airflow logo após ``stage_silver`` (ver ADR 0009).

Cada linha ganha duas colunas de linhagem:

- ``dt_ingest``     timestamp UTC da carga (usado pelo bronze incremental do dbt);
- ``_silver_table`` lote DuckDB de origem (chave de idempotência).

Re-sincronizar o mesmo lote substitui as linhas dele em vez de duplicá-las.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from govhub.ingestion import registry
from govhub.postgres import pg_engine, quote_ident

LINEAGE_COLUMNS = ("dt_ingest", "_silver_table")


def _to_json(value):
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


def flatten_structs(df: pd.DataFrame) -> pd.DataFrame:
    """Serializa colunas struct/list (dict, list, array) como texto JSON.

    O PostgreSQL não aceita esses tipos via ``to_sql``; na PoC do IBGE eles
    apareceram no aninhamento de municípios → microrregião → UF.
    """
    df = df.copy()
    for col in df.columns[df.dtypes == object]:
        if df[col].map(lambda v: isinstance(v, (dict, list, tuple, np.ndarray))).any():
            df[col] = df[col].map(_to_json)
    return df


def sync_dataframe(
    df: pd.DataFrame,
    target_table: str,
    silver_table: str,
    schema: str = "silver",
    engine: Engine | None = None,
    now: pd.Timestamp | None = None,
) -> int:
    """Grava um lote em ``<schema>.<target_table>``. Retorna o número de linhas.

    Tudo numa transação: cria o schema se preciso, adiciona colunas novas como
    TEXT, apaga as linhas do mesmo lote e insere o lote.
    """
    engine = engine or pg_engine()
    now = now if now is not None else pd.Timestamp.now(tz="UTC")
    df = flatten_structs(df).assign(dt_ingest=now, _silver_table=silver_table)

    qschema, qtable = quote_ident(schema), quote_ident(target_table)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {qschema}"))
        insp = inspect(conn)
        if insp.has_table(target_table, schema=schema):
            existing = {c["name"] for c in insp.get_columns(target_table, schema=schema)}
            for col in df.columns:
                if col not in existing:
                    conn.execute(
                        text(f"ALTER TABLE {qschema}.{qtable} ADD COLUMN {quote_ident(col)} TEXT")
                    )
            conn.execute(
                text(f"DELETE FROM {qschema}.{qtable} WHERE _silver_table = :lote"),
                {"lote": silver_table},
            )
        df.to_sql(
            target_table, conn, schema=schema, if_exists="append", index=False,
            method="multi", chunksize=1000,
        )
    return len(df)


def sync_to_postgres(
    duckdb_table: str,
    target_table: str,
    schema: str = "silver",
    engine: Engine | None = None,
) -> int:
    """Lê um lote do silver DuckDB e o sincroniza em ``<schema>.<target_table>``."""
    from govhub.ingestion.storage import silver

    df = silver.read(duckdb_table)
    return sync_dataframe(df, target_table, duckdb_table, schema=schema, engine=engine)


def airflow_task(cfg: dict, duckdb_table: str) -> int:
    """Adaptador para a task ``sync_postgres`` das DAGs de ingestão.

    ``duckdb_table`` é o valor retornado por ``stage_silver`` (o nome datado do
    lote); o destino vem do Source Registry.
    """
    return sync_to_postgres(duckdb_table, registry.target_table(cfg))

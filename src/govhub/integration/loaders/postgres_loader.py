"""
Costura C — Postgres Loader: a integração lê direto do banco.

Carrega uma tabela do PostgreSQL como ``(DataFrame, TableMetadata)``, no lugar do
CSV exportado à mão. Simétrico ao ``CsvLoader``.

Aceita ``schema.tabela``, ``pg://schema.tabela`` ou só ``tabela`` (schema ``silver``).
As colunas de linhagem do Silver Sync (``dt_ingest``, ``_silver_table``) são
removidas por padrão: são iguais entre tabelas e virariam falsas candidatas a chave.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from govhub.integration.config.settings import settings
from govhub.postgres import pg_engine, quote_ident

from .base import BaseLoader, TableMetadata

PG_PREFIX = "pg://"
DEFAULT_SCHEMA = "silver"
LINEAGE_COLUMNS = ("dt_ingest", "_silver_table")


def parse_source(source: str) -> tuple[str, str]:
    """``'pg://silver.ibge'`` → ``('silver', 'ibge')``. Schema padrão: ``silver``."""
    ref = source.removeprefix(PG_PREFIX)
    schema, _, table = ref.rpartition(".")
    schema = schema or DEFAULT_SCHEMA
    quote_ident(schema), quote_ident(table)  # valida os dois nomes
    return schema, table


def is_pg_source(source: str) -> bool:
    return source.startswith(PG_PREFIX)


class PostgresLoader(BaseLoader):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = pg_engine()
        return self._engine

    def load(
        self,
        source: str,
        table_name: str | None = None,
        sample_size: int | None = None,
        drop_lineage: bool = True,
        descriptions: dict[str, str] | None = None,
        **kwargs,
    ) -> tuple[pd.DataFrame, TableMetadata]:
        schema, table = parse_source(source)
        query = text(f"SELECT * FROM {quote_ident(schema)}.{quote_ident(table)}")
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn)

        if drop_lineage:
            df = df.drop(columns=[c for c in LINEAGE_COLUMNS if c in df.columns])

        n = sample_size or settings.sample_size
        sample = df.sample(min(n, len(df)), random_state=42) if len(df) else df
        metadata = TableMetadata.from_dataframe(
            df, table_name or f"{schema}.{table}", sample=sample, descriptions=descriptions
        )
        return df, metadata

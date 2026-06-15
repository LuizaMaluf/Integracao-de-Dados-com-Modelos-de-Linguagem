"""
Componente 3 — Postgres Loader (Costura C: integração lê do banco).

Responsabilidade: carregar uma tabela do PostgreSQL como (DataFrame, TableMetadata)
para a camada de integração, substituindo o CSV exportado à mão. Fecha a Costura C.

Destino real: integration/src/loaders/postgres_loader.py
Implementa a interface BaseLoader existente — simétrico ao CsvLoader, não-invasivo.

NOTA: stub — assinaturas e responsabilidades definidas; lógica não preenchida.
"""
from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine

# No destino real, importar de integration/src/loaders/base.py:
#   from .base import BaseLoader, TableMetadata


def _pg_engine():
    """Engine SQLAlchemy para o PostgreSQL (mesmas envs do dbt/silver_sync)."""
    user = os.environ["POSTGRES_USER"]
    pwd = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}")


class PostgresLoader:  # no destino real: class PostgresLoader(BaseLoader):
    """Carrega uma tabela do PostgreSQL como (DataFrame, TableMetadata).

    Aceita um identificador no formato `schema.tabela` (ex.: silver.ibge_municipios)
    ou uma URI `pg://schema.tabela`. Espelha a assinatura de CsvLoader.load.
    """

    def load(self, source: str, **kwargs) -> tuple:
        """Lê a tabela e devolve (df, TableMetadata).

        TODO: implementar:
          1. schema, table = parse(source)  # aceita 'schema.table' e 'pg://schema.table'
          2. df = pd.read_sql(f'SELECT * FROM "{schema}"."{table}"', _pg_engine())
          3. meta = self._build_metadata(df, f'{schema}.{table}')
          4. return df, meta
        """
        raise NotImplementedError

    def _build_metadata(self, df: pd.DataFrame, name: str):
        """Constrói TableMetadata compatível com o IntegrationAgent.

        Espelha ingestion/storage/silver.py::build_metadata.
        TODO: retornar TableMetadata(name=name, columns=..., dtypes=..., row_count=..., sample=df.head(5))."""
        raise NotImplementedError

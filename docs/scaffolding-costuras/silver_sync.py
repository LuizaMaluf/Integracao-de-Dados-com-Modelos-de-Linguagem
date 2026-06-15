"""
Componente 1 — Silver Sync (Costura A: DuckDB → PostgreSQL).

Responsabilidade: replicar cada tabela silver gravada em DuckDB para o schema
`silver` do PostgreSQL, automaticamente, ao fim de cada ingestão. Fecha a Costura A
com a ponte automática (decisão do usuário: preserva o DuckDB na ingestão).

Destino real: ingestion/storage/silver_sync.py
Roda como task do Airflow logo após `stage_silver` em api_dag.py.

NOTA: stub — assinaturas e responsabilidades definidas; lógica não preenchida.
Na PoC, a ponte foi feita por um script ad-hoc; este componente a torna permanente.
"""
from __future__ import annotations

import os

import duckdb
import pandas as pd
from sqlalchemy import create_engine


def _duckdb_conn() -> duckdb.DuckDBPyConnection:
    """Reusa a conexão DuckDB do silver (ver ingestion/storage/silver.py::_conn)."""
    path = os.environ.get("DUCKDB_PATH", "/opt/airflow/data/silver.duckdb")
    return duckdb.connect(path)


def _pg_engine():
    """Engine SQLAlchemy para o PostgreSQL analítico (mesmas envs do dbt)."""
    user = os.environ["POSTGRES_USER"]
    pwd = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}")


def _flatten_structs(df: pd.DataFrame) -> pd.DataFrame:
    """Achata colunas struct/list (ex.: aninhamento do IBGE) para tipos que o
    PostgreSQL aceita. Na PoC isto foi necessário para a tabela de municípios.

    TODO: implementar — serializar dict/list para str (ou JSONB)."""
    raise NotImplementedError


def sync_to_postgres(duckdb_table: str, target_table: str, schema: str = "silver") -> int:
    """Lê uma tabela do DuckDB e a escreve em `<schema>.<target_table>` no PostgreSQL.

    Parâmetros
    ----------
    duckdb_table : nome da tabela no silver DuckDB (ex.: ibge_municipios_20260615)
    target_table : nome estável no Postgres, sem data (ex.: ibge_municipios)
    schema       : schema de destino (default: silver)

    Retorna o número de linhas sincronizadas.

    TODO: implementar:
      1. df = _duckdb_conn().execute(f'SELECT * FROM "{duckdb_table}"').df()
      2. df = _flatten_structs(df)
      3. CREATE SCHEMA IF NOT EXISTS <schema>
      4. df.to_sql(target_table, _pg_engine(), schema=schema, if_exists='replace')
      5. retornar len(df)
    """
    raise NotImplementedError


def airflow_task(cfg: dict) -> int:
    """Adaptador para virar @task no api_dag.py, após stage_silver.

    Deriva os nomes a partir do config da fonte e chama sync_to_postgres.
    TODO: implementar a derivação de duckdb_table/target_table a partir de cfg."""
    raise NotImplementedError

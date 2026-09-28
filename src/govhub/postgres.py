"""Conexão com o PostgreSQL analítico (dbt + costuras), configurada por POSTGRES_*."""
from __future__ import annotations

import os
import re

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def pg_url() -> str:
    user = os.environ["POSTGRES_USER"]
    pwd = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


def pg_engine() -> Engine:
    """Engine SQLAlchemy para o PostgreSQL (mesmas variáveis do dbt)."""
    return create_engine(pg_url())


def quote_ident(name: str) -> str:
    """Quota um identificador já normalizado; rejeita qualquer outra coisa.

    Os nomes vêm do Source Registry e passam por ``normalize_name``; a checagem
    evita que um nome inesperado vire SQL injetado.
    """
    if not _IDENT.match(name):
        raise ValueError(f"Identificador inválido para o PostgreSQL: {name!r}")
    return f'"{name}"'

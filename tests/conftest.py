"""Fixtures compartilhadas.

Testes marcados com ``pg`` usam um PostgreSQL real, configurado pelas variáveis
POSTGRES_* (as mesmas do ``.env``). Sem banco acessível, eles são pulados.
"""
import os
import uuid

import pytest


@pytest.fixture(scope="session")
def pg_engine():
    if not os.environ.get("POSTGRES_USER"):
        pytest.skip("POSTGRES_* não configurado")
    from sqlalchemy import text

    from govhub.postgres import pg_engine as make_engine

    engine = make_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL inacessível: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture
def pg_schema(pg_engine):
    """Schema temporário, criado no início e removido ao fim do teste."""
    from sqlalchemy import text

    schema = f"test_{uuid.uuid4().hex[:8]}"
    with pg_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    yield schema
    with pg_engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))

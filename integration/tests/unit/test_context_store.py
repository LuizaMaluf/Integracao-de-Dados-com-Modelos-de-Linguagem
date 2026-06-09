"""
Unit tests for ContextStore — exercised against a mocked psycopg2 connection.
All tests follow the RED→GREEN TDD cycle.
"""
import json
from unittest.mock import MagicMock, call
import pytest

from src.store.context_store import ContextStore


# ── helpers ───────────────────────────────────────────────────────────────────

def make_store():
    """Return a ContextStore wired to a mock connection/cursor."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    # also allow non-context-manager usage: conn.cursor() → cursor
    conn.cursor.return_value = cursor
    store = ContextStore(conn)
    return store, conn, cursor


# ── domain_contexts ───────────────────────────────────────────────────────────

def test_upsert_domain_context_calls_execute():
    """upsert_domain_context must call cursor.execute with an INSERT ... ON CONFLICT SQL."""
    store, conn, cursor = make_store()

    store.upsert_domain_context(
        domain_name="budget",
        semantic_groups={"fiscal": ["empenho", "dotacao"]},
        key_patterns={"ne": r"NE\d{6}"},
        source="builtin",
    )

    assert cursor.execute.called, "cursor.execute was never called"
    sql, params = cursor.execute.call_args[0]
    sql_upper = sql.upper()
    assert "INSERT" in sql_upper
    assert "ON CONFLICT" in sql_upper
    assert "DOMAIN_CONTEXTS" in sql_upper
    # params must contain the domain name and serialised JSON for semantic_groups
    assert "budget" in params
    conn.commit.assert_called_once()


def test_get_domain_contexts_returns_list():
    """get_domain_contexts must return a list (possibly empty)."""
    store, conn, cursor = make_store()
    cursor.fetchall.return_value = []
    result = store.get_domain_contexts()
    assert isinstance(result, list)
    assert cursor.execute.called


# ── column_annotations ────────────────────────────────────────────────────────

def test_upsert_column_annotation_upsert():
    """upsert_column_annotation SQL must use ON CONFLICT DO UPDATE."""
    store, conn, cursor = make_store()

    store.upsert_column_annotation(
        table_name="empenhos",
        column_name="nr_empenho",
        domain_group="fiscal",
        semantic_tags=["identificador", "chave"],
    )

    assert cursor.execute.called
    sql, params = cursor.execute.call_args[0]
    sql_upper = sql.upper()
    assert "ON CONFLICT" in sql_upper
    assert "DO UPDATE" in sql_upper
    assert "COLUMN_ANNOTATIONS" in sql_upper
    assert "empenhos" in params
    assert "nr_empenho" in params
    conn.commit.assert_called_once()


def test_get_column_annotations_filters_by_table():
    """get_column_annotations must filter rows by the given table_name."""
    store, conn, cursor = make_store()
    cursor.fetchall.return_value = []

    store.get_column_annotations("empenhos")

    assert cursor.execute.called
    sql, params = cursor.execute.call_args[0]
    # The table filter must appear in the SQL and the param value
    assert "table_name" in sql.lower() or "%s" in sql
    assert "empenhos" in params


# ── table_profiles ────────────────────────────────────────────────────────────

def test_upsert_table_profile_calls_execute():
    """upsert_table_profile must call cursor.execute and commit."""
    store, conn, cursor = make_store()

    store.upsert_table_profile(
        table_name="contratos",
        row_count=5000,
        quality_ok=True,
    )

    assert cursor.execute.called
    sql, params = cursor.execute.call_args[0]
    assert "TABLE_PROFILES" in sql.upper()
    assert "contratos" in params
    conn.commit.assert_called_once()


def test_get_table_profile_returns_none_on_miss():
    """get_table_profile must return None when no row is found."""
    store, conn, cursor = make_store()
    cursor.fetchone.return_value = None

    result = store.get_table_profile("nonexistent_table")
    assert result is None


# ── integration_discoveries ───────────────────────────────────────────────────

def test_upsert_discovery_uses_greatest_confidence():
    """upsert_discovery SQL must use GREATEST(...) to keep the best confidence score."""
    store, conn, cursor = make_store()

    store.upsert_discovery(
        table_a="empenhos",
        column_a="nr_empenho",
        table_b="contratos",
        column_b="id_contrato",
        confidence=0.92,
        discovery_method="semantic",
        justification="matching SIAFI pattern",
    )

    assert cursor.execute.called
    sql, params = cursor.execute.call_args[0]
    assert "GREATEST" in sql.upper()
    assert "INTEGRATION_DISCOVERIES" in sql.upper()
    assert 0.92 in params
    conn.commit.assert_called_once()


def test_get_discoveries_filters_validated_false():
    """get_discoveries must exclude rows where is_validated = FALSE."""
    store, conn, cursor = make_store()
    cursor.fetchall.return_value = []

    store.get_discoveries("empenhos", min_confidence=0.7)

    assert cursor.execute.called
    sql, params = cursor.execute.call_args[0]
    # The query must contain a filter that rejects is_validated = FALSE
    # Typical pattern: IS NOT FALSE  or  (is_validated IS NULL OR is_validated = TRUE)
    sql_norm = sql.upper().replace("\n", " ").replace("  ", " ")
    has_not_false = "IS NOT FALSE" in sql_norm
    has_explicit = ("IS NULL" in sql_norm and "TRUE" in sql_norm)
    assert has_not_false or has_explicit, (
        "SQL must filter out is_validated = FALSE; got:\n" + sql
    )


def test_get_discoveries_filters_by_min_confidence():
    """get_discoveries must apply a >= min_confidence filter in the WHERE clause."""
    store, conn, cursor = make_store()
    cursor.fetchall.return_value = []

    store.get_discoveries("empenhos", min_confidence=0.85)

    sql, params = cursor.execute.call_args[0]
    assert "confidence" in sql.lower()
    assert 0.85 in params


def test_validate_discovery_sets_flag():
    """validate_discovery must UPDATE is_validated and last_confirmed_at."""
    store, conn, cursor = make_store()

    store.validate_discovery(
        table_a="empenhos",
        column_a="nr_empenho",
        table_b="contratos",
        column_b="id_contrato",
        is_valid=True,
    )

    assert cursor.execute.called
    sql, params = cursor.execute.call_args[0]
    sql_upper = sql.upper()
    assert "UPDATE" in sql_upper
    assert "IS_VALIDATED" in sql_upper
    assert True in params
    conn.commit.assert_called_once()

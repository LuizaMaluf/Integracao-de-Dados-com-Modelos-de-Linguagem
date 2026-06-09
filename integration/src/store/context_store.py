"""
ContextStore — passive PostgreSQL client for the `context` schema.

Design decisions:
- Receives a live psycopg2 connection (or any object with .cursor() / .commit())
  at construction time.  Never opens a connection itself; simplifies testing and
  lets callers own transaction / connection-pool lifecycle.
- All JSONB fields are serialised explicitly with json.dumps so the driver never
  has to guess the wire type.
- upsert_discovery uses GREATEST(existing, excluded) so a lower-confidence
  re-run never overwrites a higher-confidence prior result.
- get_discoveries filters `is_validated IS NOT FALSE` — NULL (unreviewed) rows
  are included; only explicitly rejected rows are excluded.
"""
from __future__ import annotations

import json
from typing import Any


class ContextStore:
    """CRUD façade over the `context` PostgreSQL schema."""

    def __init__(self, conn: Any) -> None:
        """
        Parameters
        ----------
        conn:
            A psycopg2 connection (or compatible mock) that exposes
            .cursor(), .commit(), and .rollback().
        """
        self._conn = conn

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cursor(self):
        return self._conn.cursor()

    # ------------------------------------------------------------------
    # domain_contexts
    # ------------------------------------------------------------------

    def upsert_domain_context(
        self,
        domain_name: str,
        semantic_groups: dict,
        key_patterns: dict | None = None,
        source: str = "builtin",
    ) -> None:
        """Insert or replace a domain context entry."""
        sql = """
            INSERT INTO context.domain_contexts
                (domain_name, semantic_groups, key_patterns, source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (domain_name) DO UPDATE SET
                semantic_groups = EXCLUDED.semantic_groups,
                key_patterns    = EXCLUDED.key_patterns,
                source          = EXCLUDED.source
        """
        params = (
            domain_name,
            json.dumps(semantic_groups),
            json.dumps(key_patterns) if key_patterns is not None else None,
            source,
        )
        cur = self._cursor()
        cur.execute(sql, params)
        self._conn.commit()

    def get_domain_contexts(self) -> list[dict]:
        """Return all domain context records."""
        sql = """
            SELECT domain_name, semantic_groups, key_patterns, source, created_at
            FROM context.domain_contexts
            ORDER BY domain_name
        """
        cur = self._cursor()
        cur.execute(sql, ())
        rows = cur.fetchall()
        return [
            {
                "domain_name": r[0],
                "semantic_groups": r[1],
                "key_patterns": r[2],
                "source": r[3],
                "created_at": r[4],
            }
            for r in (rows or [])
        ]

    # ------------------------------------------------------------------
    # column_annotations
    # ------------------------------------------------------------------

    def upsert_column_annotation(
        self,
        table_name: str,
        column_name: str,
        domain_group: str | None = None,
        semantic_tags: list[str] | None = None,
    ) -> None:
        """Insert or update a column annotation."""
        sql = """
            INSERT INTO context.column_annotations
                (table_name, column_name, domain_group, semantic_tags)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (table_name, column_name) DO UPDATE SET
                domain_group  = EXCLUDED.domain_group,
                semantic_tags = EXCLUDED.semantic_tags,
                detected_at   = now()
        """
        params = (
            table_name,
            column_name,
            domain_group,
            semantic_tags,
        )
        cur = self._cursor()
        cur.execute(sql, params)
        self._conn.commit()

    def get_column_annotations(self, table_name: str) -> list[dict]:
        """Return all column annotations for a given table."""
        sql = """
            SELECT table_name, column_name, domain_group, semantic_tags, detected_at
            FROM context.column_annotations
            WHERE table_name = %s
            ORDER BY column_name
        """
        params = (table_name,)
        cur = self._cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [
            {
                "table_name": r[0],
                "column_name": r[1],
                "domain_group": r[2],
                "semantic_tags": r[3],
                "detected_at": r[4],
            }
            for r in (rows or [])
        ]

    # ------------------------------------------------------------------
    # table_profiles
    # ------------------------------------------------------------------

    def upsert_table_profile(
        self,
        table_name: str,
        row_count: int | None = None,
        exercicio_distribution: dict | None = None,
        cardinality_per_col: dict | None = None,
        quality_ok: bool | None = None,
    ) -> None:
        """Insert or replace a table profile."""
        sql = """
            INSERT INTO context.table_profiles
                (table_name, row_count, exercicio_distribution,
                 cardinality_per_col, quality_ok)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (table_name) DO UPDATE SET
                row_count               = EXCLUDED.row_count,
                exercicio_distribution  = EXCLUDED.exercicio_distribution,
                cardinality_per_col     = EXCLUDED.cardinality_per_col,
                quality_ok              = EXCLUDED.quality_ok,
                profiled_at             = now()
        """
        params = (
            table_name,
            row_count,
            json.dumps(exercicio_distribution) if exercicio_distribution is not None else None,
            json.dumps(cardinality_per_col) if cardinality_per_col is not None else None,
            quality_ok,
        )
        cur = self._cursor()
        cur.execute(sql, params)
        self._conn.commit()

    def get_table_profile(self, table_name: str) -> dict | None:
        """Return the profile for a table, or None if not found."""
        sql = """
            SELECT table_name, row_count, exercicio_distribution,
                   cardinality_per_col, quality_ok, profiled_at
            FROM context.table_profiles
            WHERE table_name = %s
        """
        cur = self._cursor()
        cur.execute(sql, (table_name,))
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "table_name": row[0],
            "row_count": row[1],
            "exercicio_distribution": row[2],
            "cardinality_per_col": row[3],
            "quality_ok": row[4],
            "profiled_at": row[5],
        }

    # ------------------------------------------------------------------
    # integration_discoveries
    # ------------------------------------------------------------------

    def upsert_discovery(
        self,
        table_a: str,
        column_a: str,
        table_b: str,
        column_b: str,
        confidence: float,
        discovery_method: str | None = None,
        justification: str | None = None,
        evidence_for: dict | None = None,
        evidence_against: dict | None = None,
        required_transforms: dict | None = None,
    ) -> None:
        """
        Insert or update an integration discovery.

        On conflict, keeps the GREATEST confidence value so that a lower-
        scoring re-run never silently downgrades a previously good result.
        All other mutable fields are overwritten by the incoming values.
        """
        sql = """
            INSERT INTO context.integration_discoveries
                (table_a, column_a, table_b, column_b,
                 confidence, discovery_method, justification,
                 evidence_for, evidence_against, required_transforms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (table_a, column_a, table_b, column_b) DO UPDATE SET
                confidence          = GREATEST(EXCLUDED.confidence,
                                              context.integration_discoveries.confidence),
                discovery_method    = EXCLUDED.discovery_method,
                justification       = EXCLUDED.justification,
                evidence_for        = EXCLUDED.evidence_for,
                evidence_against    = EXCLUDED.evidence_against,
                required_transforms = EXCLUDED.required_transforms,
                last_confirmed_at   = now()
        """
        params = (
            table_a,
            column_a,
            table_b,
            column_b,
            confidence,
            discovery_method,
            justification,
            json.dumps(evidence_for) if evidence_for is not None else None,
            json.dumps(evidence_against) if evidence_against is not None else None,
            json.dumps(required_transforms) if required_transforms is not None else None,
        )
        cur = self._cursor()
        cur.execute(sql, params)
        self._conn.commit()

    def get_discoveries(
        self,
        table_name: str,
        min_confidence: float = 0.7,
    ) -> list[dict]:
        """
        Return integration discoveries involving *table_name* (as table_a OR
        table_b) with confidence >= min_confidence and is_validated IS NOT FALSE.
        """
        sql = """
            SELECT table_a, column_a, table_b, column_b,
                   confidence, discovery_method, justification,
                   evidence_for, evidence_against, required_transforms,
                   is_validated, discovered_at, last_confirmed_at
            FROM context.integration_discoveries
            WHERE (table_a = %s OR table_b = %s)
              AND confidence >= %s
              AND is_validated IS NOT FALSE
            ORDER BY confidence DESC
        """
        params = (table_name, table_name, min_confidence)
        cur = self._cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [
            {
                "table_a": r[0],
                "column_a": r[1],
                "table_b": r[2],
                "column_b": r[3],
                "confidence": r[4],
                "discovery_method": r[5],
                "justification": r[6],
                "evidence_for": r[7],
                "evidence_against": r[8],
                "required_transforms": r[9],
                "is_validated": r[10],
                "discovered_at": r[11],
                "last_confirmed_at": r[12],
            }
            for r in (rows or [])
        ]

    def validate_discovery(
        self,
        table_a: str,
        column_a: str,
        table_b: str,
        column_b: str,
        is_valid: bool,
    ) -> None:
        """Mark a discovery as validated (True) or rejected (False)."""
        sql = """
            UPDATE context.integration_discoveries
            SET is_validated      = %s,
                last_confirmed_at = now()
            WHERE table_a = %s
              AND column_a = %s
              AND table_b  = %s
              AND column_b = %s
        """
        params = (is_valid, table_a, column_a, table_b, column_b)
        cur = self._cursor()
        cur.execute(sql, params)
        self._conn.commit()

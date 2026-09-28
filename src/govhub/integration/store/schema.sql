-- Context Store DDL
-- Passive schema that accumulates domain knowledge and integration discoveries
-- across pipeline runs.  Apply once per environment:
--   psql -U <user> -d <db> -f schema.sql

CREATE SCHEMA IF NOT EXISTS context;

-- --------------------------------------------------------------------------
-- domain_contexts
-- Stores named domain vocabularies (semantic_groups + key_patterns).
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS context.domain_contexts (
    domain_name     TEXT PRIMARY KEY,
    semantic_groups JSONB NOT NULL,
    key_patterns    JSONB,
    source          TEXT NOT NULL CHECK (source IN ('builtin', 'user-defined')),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- --------------------------------------------------------------------------
-- column_annotations
-- Per-column semantic metadata discovered or user-annotated.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS context.column_annotations (
    table_name    TEXT NOT NULL,
    column_name   TEXT NOT NULL,
    domain_group  TEXT,
    semantic_tags TEXT[],
    detected_at   TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (table_name, column_name)
);

-- --------------------------------------------------------------------------
-- table_profiles
-- Statistical profile of a table captured at profiling time.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS context.table_profiles (
    table_name              TEXT PRIMARY KEY,
    row_count               INTEGER,
    exercicio_distribution  JSONB,
    cardinality_per_col     JSONB,
    quality_ok              BOOLEAN,
    profiled_at             TIMESTAMPTZ DEFAULT now()
);

-- --------------------------------------------------------------------------
-- integration_discoveries
-- Candidate integration keys found by the IntegrationAgent.
-- is_validated = NULL  → not yet reviewed
-- is_validated = TRUE  → confirmed by a human/downstream rule
-- is_validated = FALSE → rejected; excluded from active results
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS context.integration_discoveries (
    table_a              TEXT NOT NULL,
    column_a             TEXT NOT NULL,
    table_b              TEXT NOT NULL,
    column_b             TEXT NOT NULL,
    confidence           FLOAT NOT NULL,
    discovery_method     TEXT,
    justification        TEXT,
    evidence_for         JSONB,
    evidence_against     JSONB,
    required_transforms  JSONB,
    is_validated         BOOLEAN DEFAULT NULL,
    discovered_at        TIMESTAMPTZ DEFAULT now(),
    last_confirmed_at    TIMESTAMPTZ,
    PRIMARY KEY (table_a, column_a, table_b, column_b)
);

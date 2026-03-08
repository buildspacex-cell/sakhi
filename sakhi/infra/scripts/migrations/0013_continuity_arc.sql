-- 0013_continuity_arc.sql
-- Continuity arc policy + explicit per-source labels for deterministic arc building.

CREATE TABLE IF NOT EXISTS continuity_surface_policy (
    person_id    UUID NOT NULL,
    scope        TEXT NOT NULL,
    enabled      BOOLEAN NOT NULL DEFAULT false,
    exclusions   JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (person_id, scope)
);

CREATE TABLE IF NOT EXISTS continuity_labels (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id    UUID NOT NULL,
    source_type  TEXT NOT NULL,
    source_id    TEXT NOT NULL,
    anchor       TEXT NOT NULL,
    facets       JSONB NOT NULL DEFAULT '[]'::jsonb,
    entities     JSONB NOT NULL DEFAULT '[]'::jsonb,
    scalar       DOUBLE PRECISION,
    metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT continuity_labels_source_unique UNIQUE (person_id, source_type, source_id)
);

CREATE INDEX IF NOT EXISTS idx_continuity_labels_anchor
    ON continuity_labels (person_id, anchor, source_type, created_at DESC);

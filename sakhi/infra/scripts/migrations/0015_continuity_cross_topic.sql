-- 0015_continuity_cross_topic.sql
-- Cross-topic continuity cache tables (pairwise correlations + life dimensions).

CREATE TABLE IF NOT EXISTS continuity_topic_correlations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id           UUID NOT NULL,
    topic_key_a         TEXT NOT NULL,
    topic_key_b         TEXT NOT NULL,
    combined_score      DOUBLE PRECISION NOT NULL,
    temporal_score      DOUBLE PRECISION NOT NULL DEFAULT 0,
    semantic_score      DOUBLE PRECISION NOT NULL DEFAULT 0,
    facet_score         DOUBLE PRECISION NOT NULL DEFAULT 0,
    directional_score   DOUBLE PRECISION NOT NULL DEFAULT 0,
    correlation_types   JSONB NOT NULL DEFAULT '[]'::jsonb,
    shared_facets       JSONB NOT NULL DEFAULT '[]'::jsonb,
    overlap_windows     JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_window_start TIMESTAMPTZ,
    source_window_end   TIMESTAMPTZ,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT continuity_topic_corr_pair_unique UNIQUE (person_id, topic_key_a, topic_key_b),
    CONSTRAINT continuity_topic_corr_pair_order CHECK (topic_key_a < topic_key_b)
);

CREATE INDEX IF NOT EXISTS idx_continuity_topic_corr_person_score
    ON continuity_topic_correlations (person_id, combined_score DESC, computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_continuity_topic_corr_person_topic_a
    ON continuity_topic_correlations (person_id, topic_key_a, computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_continuity_topic_corr_person_topic_b
    ON continuity_topic_correlations (person_id, topic_key_b, computed_at DESC);


CREATE TABLE IF NOT EXISTS continuity_life_dimensions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id        UUID NOT NULL,
    dimension        TEXT NOT NULL,
    signal_level     DOUBLE PRECISION NOT NULL,
    signal_direction TEXT NOT NULL,
    affected_topics  TEXT[] NOT NULL DEFAULT '{}'::text[],
    evidence_summary TEXT,
    signal_markers   JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT continuity_life_dimensions_unique UNIQUE (person_id, dimension),
    CONSTRAINT continuity_life_dimensions_dimension_check
        CHECK (dimension IN ('time_availability', 'financial_pressure', 'emotional_bandwidth')),
    CONSTRAINT continuity_life_dimensions_direction_check
        CHECK (signal_direction IN ('pressured', 'neutral', 'resourced'))
);

CREATE INDEX IF NOT EXISTS idx_continuity_life_dimensions_person
    ON continuity_life_dimensions (person_id, computed_at DESC);

-- Build 37 – Memory Synthesis schema
-- Weekly + monthly reflections, drift tracking, and semantic compression

CREATE TABLE IF NOT EXISTS memory_weekly_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    highlights TEXT,
    top_themes JSONB NOT NULL DEFAULT '[]'::jsonb,
    drift_score NUMERIC NOT NULL DEFAULT 0.0,
    semantic_notes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, week_start)
);

CREATE TABLE IF NOT EXISTS memory_monthly_recaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    month_scope DATERANGE NOT NULL,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    highlights TEXT,
    top_themes JSONB NOT NULL DEFAULT '[]'::jsonb,
    chapter_hint TEXT,
    drift_score NUMERIC NOT NULL DEFAULT 0.0,
    compression JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, month_scope)
);

CREATE TABLE IF NOT EXISTS memory_theme_drift_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    horizon TEXT NOT NULL,
    from_theme TEXT,
    to_theme TEXT,
    drift_score NUMERIC NOT NULL DEFAULT 0.0,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS memory_theme_drift_person_idx
    ON memory_theme_drift_events (person_id, created_at DESC);

CREATE TABLE IF NOT EXISTS memory_semantic_rollups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    source_id UUID NOT NULL,
    source_kind TEXT NOT NULL,
    semantic_summary TEXT NOT NULL,
    strength NUMERIC NOT NULL DEFAULT 0.0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, source_id, source_kind)
);

CREATE TABLE IF NOT EXISTS memory_strength_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    event_kind TEXT NOT NULL,         -- strengthen | forget
    target TEXT NOT NULL,
    weight NUMERIC NOT NULL DEFAULT 0.0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS memory_strength_person_idx
    ON memory_strength_events (person_id, created_at DESC);

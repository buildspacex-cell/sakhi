-- Weekly signals (language-free aggregation for reflection inputs).

CREATE TABLE IF NOT EXISTS memory_weekly_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    episodic_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    theme_stats JSONB NOT NULL DEFAULT '[]'::jsonb,
    contrast_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    delta_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence NUMERIC NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, week_start)
);

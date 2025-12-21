-- Backfill: memory_context_cache table keyed by profiles.user_id

CREATE TABLE IF NOT EXISTS memory_context_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    window_kind TEXT NOT NULL DEFAULT 'default',
    entries JSONB NOT NULL DEFAULT '[]'::jsonb,
    rhythm_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    persona_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    task_window JSONB NOT NULL DEFAULT '[]'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS memory_context_cache_user_idx
    ON memory_context_cache(user_id, window_kind);

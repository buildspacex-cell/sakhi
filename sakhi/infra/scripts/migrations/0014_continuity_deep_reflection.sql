CREATE TABLE IF NOT EXISTS deep_reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    topic_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed')),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    inputs_hash TEXT NOT NULL,
    result_json JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS deep_reflections_person_topic_created_idx
    ON deep_reflections (person_id, topic_key, created_at DESC);

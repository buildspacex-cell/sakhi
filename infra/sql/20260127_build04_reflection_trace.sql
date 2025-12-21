-- Build 04 (Phase-2): Reflection Trace table
-- Deterministic, turn-scoped, 30-day TTL handled by ops/cron (not in this migration).

BEGIN;

CREATE TABLE IF NOT EXISTS reflection_traces (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    turn_id UUID NOT NULL UNIQUE,
    session_id UUID,
    moment_model JSONB DEFAULT '{}'::jsonb,
    evidence_pack JSONB DEFAULT '{}'::jsonb,
    deliberation_scaffold JSONB DEFAULT '{}'::jsonb,
    trace JSONB DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION DEFAULT 0.0,
    low_confidence BOOLEAN DEFAULT FALSE,
    recommend_caution BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reflection_traces_person_created
    ON reflection_traces (person_id, created_at DESC);

COMMIT;

-- Build 98: Micro Journey cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS micro_journey_cache (
    person_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    journey JSONB NOT NULL,
    flow_count INT NOT NULL,
    rhythm_slot TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (person_id)
);

CREATE INDEX IF NOT EXISTS micro_journey_cache_updated_idx
    ON micro_journey_cache (generated_at DESC);

COMMIT;

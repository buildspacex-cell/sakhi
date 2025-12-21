-- Build 96: Mini-Flow cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS mini_flow_cache (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    flow_date DATE NOT NULL,
    warmup_step TEXT DEFAULT '',
    focus_block_step TEXT DEFAULT '',
    closure_step TEXT DEFAULT '',
    optional_reward TEXT DEFAULT '',
    source TEXT DEFAULT '',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT mini_flow_person_date UNIQUE (person_id, flow_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS mini_flow_state JSONB DEFAULT '{}'::jsonb;

COMMIT;

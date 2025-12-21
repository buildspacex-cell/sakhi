-- Longitudinal trend deltas: structured, non-narrative, time-aware
ALTER TABLE personal_model
    ADD COLUMN IF NOT EXISTS longitudinal_state jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN personal_model.longitudinal_state IS
    'Stores only structured longitudinal deltas (direction/volatility/confidence/window). No prose, no reflection summaries, no identity labels.';

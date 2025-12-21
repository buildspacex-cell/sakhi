-- Build 72: Emotion Loop Engine v2

BEGIN;

ALTER TABLE IF EXISTS memory_episodic
    ADD COLUMN IF NOT EXISTS emotion_loop JSONB DEFAULT '{}'::jsonb;

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS emotion_state JSONB DEFAULT '{}'::jsonb;

COMMIT;


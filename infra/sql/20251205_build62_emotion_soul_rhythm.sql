-- Build 62: Emotion × Soul × Rhythm coherence state

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS emotion_soul_rhythm_state JSONB DEFAULT '{}'::jsonb;


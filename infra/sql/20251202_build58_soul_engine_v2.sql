-- Build 58: Soul Engine v2 (Shadow/Light/Friction/Conflict)

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS soul_shadow JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS soul_light JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS soul_conflicts JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS soul_friction JSONB DEFAULT '{}'::jsonb;

ALTER TABLE IF EXISTS memory_episodic
    ADD COLUMN IF NOT EXISTS soul_shadow JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS soul_light JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS soul_conflict JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS soul_friction JSONB DEFAULT '{}'::jsonb;

ALTER TABLE IF EXISTS memory_short_term
    ADD COLUMN IF NOT EXISTS soul_shadow JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS soul_light JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_pm_soul_shadow ON personal_model USING GIN (soul_shadow);
CREATE INDEX IF NOT EXISTS idx_ep_soul_shadow ON memory_episodic USING GIN (soul_shadow);

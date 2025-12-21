-- Build 65: Identity Timeline & Persona Evolution

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS identity_timeline JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS persona_evolution_state JSONB DEFAULT '{}'::jsonb;


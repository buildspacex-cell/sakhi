-- Build 63: Identity Momentum state

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS identity_momentum_state JSONB DEFAULT '{}'::jsonb;


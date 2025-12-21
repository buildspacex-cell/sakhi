-- Build 85: Session Continuity (12h rolling conversation state)

BEGIN;

CREATE TABLE IF NOT EXISTS session_continuity (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    continuity_state JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMIT;

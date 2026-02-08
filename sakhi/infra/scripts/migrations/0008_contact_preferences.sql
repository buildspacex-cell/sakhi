-- =============================================================================
-- Migration 0008: Contact Preferences & Priority System
-- =============================================================================
--
-- Adds a channel-agnostic contact preferences table that lets users define
-- relationships and priorities for their contacts. Used to personalize
-- email digest triage and future messaging channel triage.
--
-- Part of: Priority 1 — Contact Preferences (EXECUTION_PRIORITY.md)
-- Design:  docs/features/unified-messaging-strategy.md → Contact Preferences
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS contact_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Contact identification (works across channels)
    contact_identifier TEXT NOT NULL,       -- email address, phone number, Slack handle
    channel TEXT NOT NULL DEFAULT 'email',  -- email, slack, teams, whatsapp, etc.

    -- Relationship
    display_name TEXT,                      -- "Sarah Chen"
    relationship TEXT,                      -- boss, family, colleague, client, vendor, friend
    organization TEXT,                      -- "Acme Corp", "Mom's side"

    -- Priority
    priority TEXT NOT NULL DEFAULT 'normal', -- critical, high, normal, low, muted

    -- Behavior notes (for LLM context)
    notes TEXT,                             -- "Always reply same day", "Can wait until Monday"

    -- Auto-learned
    learned_from TEXT DEFAULT 'user_set',   -- user_set, dismiss_pattern, reply_speed
    confidence FLOAT DEFAULT 1.0,          -- 1.0 for user-set, lower for inferred

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(person_id, contact_identifier, channel)
);

COMMENT ON TABLE contact_preferences
    IS 'User-defined contact priorities and relationships. Channel-agnostic — works for email, Slack, Teams, etc.';

-- ---------------------------------------------------------------------------
-- 2. Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_contact_preferences_person_priority
    ON contact_preferences(person_id, priority);

CREATE INDEX IF NOT EXISTS idx_contact_preferences_person_contact
    ON contact_preferences(person_id, contact_identifier);

-- ---------------------------------------------------------------------------
-- 3. Row-Level Security
-- ---------------------------------------------------------------------------

ALTER TABLE contact_preferences ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS contact_preferences_user_policy ON contact_preferences;
CREATE POLICY contact_preferences_user_policy ON contact_preferences
    FOR ALL USING (person_id = auth.uid());

-- ---------------------------------------------------------------------------
-- 4. Updated-at trigger (reuse existing function)
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_contact_preferences_updated_at ON contact_preferences;
CREATE TRIGGER trg_contact_preferences_updated_at
    BEFORE UPDATE ON contact_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_email_updated_at();

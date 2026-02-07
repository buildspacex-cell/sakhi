-- Migration: 0007_commitment_types_and_dismissed_actions
-- Description: Add commitment_type to email_commitments + dismissed actions table
-- Date: 2026-02-07
--
-- Changes:
-- 1. Add commitment_type column to email_commitments ('people' vs 'subscription')
-- 2. Create email_dismissed_actions table for persistent action item dismissal

-- =============================================================================
-- 1. ADD COMMITMENT_TYPE TO EMAIL_COMMITMENTS
-- =============================================================================

ALTER TABLE email_commitments
    ADD COLUMN IF NOT EXISTS commitment_type TEXT NOT NULL DEFAULT 'people';

COMMENT ON COLUMN email_commitments.commitment_type
    IS 'people = promise to a real person, subscription = membership/renewal/billing tracker';

-- Index for filtering by type
CREATE INDEX IF NOT EXISTS idx_email_commitments_person_type
    ON email_commitments(person_id, commitment_type, status);

-- =============================================================================
-- 2. DISMISSED ACTION ITEMS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS email_dismissed_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL,
    dismissed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(person_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_email_dismissed_actions_person
    ON email_dismissed_actions(person_id);

COMMENT ON TABLE email_dismissed_actions
    IS 'Tracks action items the user has dismissed (persists across digest regenerations)';

-- RLS
ALTER TABLE email_dismissed_actions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS email_dismissed_actions_user_policy ON email_dismissed_actions;
CREATE POLICY email_dismissed_actions_user_policy ON email_dismissed_actions
    FOR ALL USING (person_id = auth.uid());

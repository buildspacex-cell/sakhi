-- Migration: 0006_email_commitments
-- Description: Persistent email commitment tracking
-- Date: 2026-02-07
--
-- Commitments extracted from sent emails persist across digest regenerations.
-- Users can mark commitments as done or dismissed.

-- =============================================================================
-- EMAIL_COMMITMENTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS email_commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Deduplication
    commitment_hash TEXT NOT NULL,  -- SHA256(commitment + recipient + subject)

    -- Content (from LLM extraction)
    commitment TEXT NOT NULL,
    deadline TEXT,          -- Natural language deadline from LLM
    subject TEXT,           -- Email subject the commitment came from
    recipient TEXT,         -- Who the user promised to
    source_digest_id UUID,  -- Which digest generated this commitment

    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'active',  -- active, done, dismissed
    status_changed_at TIMESTAMPTZ,

    -- Timestamps
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One commitment per person (dedup by hash)
    UNIQUE(person_id, commitment_hash)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_commitments_person_status
    ON email_commitments(person_id, status);

CREATE INDEX IF NOT EXISTS idx_email_commitments_extracted
    ON email_commitments(person_id, extracted_at DESC);

-- Comments
COMMENT ON TABLE email_commitments IS 'Persistent email commitments extracted from sent emails';
COMMENT ON COLUMN email_commitments.commitment_hash IS 'SHA256 for dedup across digest regenerations';
COMMENT ON COLUMN email_commitments.status IS 'active = tracked, done = completed, dismissed = removed by user';

-- RLS
ALTER TABLE email_commitments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS email_commitments_user_policy ON email_commitments;
CREATE POLICY email_commitments_user_policy ON email_commitments
    FOR ALL USING (person_id = auth.uid());

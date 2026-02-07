-- Migration: 0004_email_intelligence
-- Description: Email Intelligence Integration tables for Sakhi
-- Date: 2026-02-07
--
-- This migration creates tables for:
-- - email_sync_state: OAuth tokens and sync state per provider
-- - email_events: Normalized email metadata (no body content stored)
-- - email_signals: Extracted intelligence signals
--
-- Philosophy: Email is a signal generator, not a content store.
-- We store minimal metadata to extract patterns, not archive emails.

-- =============================================================================
-- EMAIL_SYNC_STATE TABLE
-- =============================================================================
-- Stores OAuth credentials and sync state per user per provider

CREATE TABLE IF NOT EXISTS email_sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,  -- 'gmail', 'outlook', etc.
    status TEXT NOT NULL DEFAULT 'connecting',  -- connecting, syncing, active, paused, error

    -- OAuth tokens (encrypted)
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,

    -- Sync state
    connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sync_at TIMESTAMPTZ,
    last_history_id TEXT,  -- Provider-specific cursor for incremental sync
    messages_synced INTEGER NOT NULL DEFAULT 0,

    -- Error tracking
    error_message TEXT,
    error_at TIMESTAMPTZ,
    consecutive_errors INTEGER NOT NULL DEFAULT 0,

    -- User control
    paused_at TIMESTAMPTZ,
    paused_by_user BOOLEAN NOT NULL DEFAULT FALSE,
    sync_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one provider per user
    UNIQUE(person_id, provider)
);

-- Idempotent: add missing columns if table already exists from prior migration
ALTER TABLE email_sync_state ADD COLUMN IF NOT EXISTS messages_synced INTEGER NOT NULL DEFAULT 0;
ALTER TABLE email_sync_state ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE email_sync_state ADD COLUMN IF NOT EXISTS error_at TIMESTAMPTZ;
ALTER TABLE email_sync_state ADD COLUMN IF NOT EXISTS consecutive_errors INTEGER NOT NULL DEFAULT 0;
ALTER TABLE email_sync_state ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ;
ALTER TABLE email_sync_state ADD COLUMN IF NOT EXISTS paused_by_user BOOLEAN NOT NULL DEFAULT FALSE;
-- Rename history_id → last_history_id if old column exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'email_sync_state' AND column_name = 'history_id') THEN
        ALTER TABLE email_sync_state RENAME COLUMN history_id TO last_history_id;
    END IF;
END $$;
ALTER TABLE email_sync_state ADD COLUMN IF NOT EXISTS last_history_id TEXT;

-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_email_sync_state_person
    ON email_sync_state(person_id);

CREATE INDEX IF NOT EXISTS idx_email_sync_state_status
    ON email_sync_state(status);

-- Comment
COMMENT ON TABLE email_sync_state IS 'OAuth credentials and sync state for email providers';
COMMENT ON COLUMN email_sync_state.access_token_encrypted IS 'Fernet-encrypted OAuth access token';
COMMENT ON COLUMN email_sync_state.refresh_token_encrypted IS 'Fernet-encrypted OAuth refresh token';
COMMENT ON COLUMN email_sync_state.last_history_id IS 'Provider-specific sync cursor (e.g., Gmail historyId)';


-- =============================================================================
-- EMAIL_EVENTS TABLE
-- =============================================================================
-- Normalized email metadata. No body content stored.

CREATE TABLE IF NOT EXISTS email_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,

    -- Message identifiers
    message_id TEXT NOT NULL,  -- Normalized message ID
    thread_id TEXT NOT NULL,   -- Provider's thread ID
    provider_message_id TEXT,  -- Original provider message ID

    -- Timing
    timestamp TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ,  -- When received (for latency analysis)

    -- Direction
    direction TEXT NOT NULL,  -- 'incoming' or 'outgoing'

    -- Participants (minimal)
    sender_email TEXT NOT NULL,
    sender_name TEXT,
    sender_domain TEXT,
    recipient_count INTEGER DEFAULT 1,

    -- Thread metadata
    subject TEXT,
    is_reply BOOLEAN DEFAULT FALSE,

    -- Attachment info
    has_attachments BOOLEAN DEFAULT FALSE,
    attachment_count INTEGER DEFAULT 0,

    -- Classification flags
    is_newsletter BOOLEAN DEFAULT FALSE,
    is_automated BOOLEAN DEFAULT FALSE,
    is_promotional BOOLEAN DEFAULT FALSE,
    is_read BOOLEAN DEFAULT TRUE,
    is_starred BOOLEAN DEFAULT FALSE,
    is_important BOOLEAN DEFAULT FALSE,

    -- Headers for signal extraction
    has_unsubscribe BOOLEAN DEFAULT FALSE,
    header_list_unsubscribe TEXT,
    header_auto_submitted TEXT,
    header_precedence TEXT,

    -- Labels (provider-specific, stored as JSON)
    labels JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one message per person
    UNIQUE(person_id, message_id)
);

-- Idempotent: add missing columns if table already exists from prior migration
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS provider_message_id TEXT;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS has_attachments BOOLEAN DEFAULT FALSE;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS attachment_count INTEGER DEFAULT 0;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT TRUE;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT FALSE;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS is_important BOOLEAN DEFAULT FALSE;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS header_list_unsubscribe TEXT;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS header_auto_submitted TEXT;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS header_precedence TEXT;

-- Fix unique constraint: change from (person_id, provider, message_id) to (person_id, message_id)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'email_events_person_id_provider_message_id_key'
    ) THEN
        ALTER TABLE email_events DROP CONSTRAINT email_events_person_id_provider_message_id_key;
    END IF;
END $$;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'email_events_person_id_message_id_key'
    ) THEN
        ALTER TABLE email_events ADD CONSTRAINT email_events_person_id_message_id_key UNIQUE (person_id, message_id);
    END IF;
END $$;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_email_events_person_timestamp
    ON email_events(person_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_email_events_thread
    ON email_events(person_id, thread_id);

CREATE INDEX IF NOT EXISTS idx_email_events_sender_domain
    ON email_events(person_id, sender_domain);

CREATE INDEX IF NOT EXISTS idx_email_events_direction
    ON email_events(person_id, direction, timestamp DESC);

-- Partial index for newsletters (efficient subscription analysis)
CREATE INDEX IF NOT EXISTS idx_email_events_newsletter
    ON email_events(person_id, sender_email, timestamp)
    WHERE is_newsletter = TRUE OR has_unsubscribe = TRUE;

-- Comment
COMMENT ON TABLE email_events IS 'Normalized email metadata for signal extraction. No body content.';
COMMENT ON COLUMN email_events.direction IS 'incoming = received, outgoing = sent';
COMMENT ON COLUMN email_events.has_unsubscribe IS 'Has List-Unsubscribe header';


-- =============================================================================
-- EMAIL_SIGNALS TABLE
-- =============================================================================
-- Extracted intelligence signals from email patterns

CREATE TABLE IF NOT EXISTS email_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Signal type
    signal_type TEXT NOT NULL,  -- 'subscription', 'avoidance', 'boundary_erosion', 'cognitive_load'

    -- Signal data (JSON blob with type-specific structure)
    signal_data JSONB NOT NULL,

    -- Confidence and timing
    confidence FLOAT DEFAULT 0.5,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- For time-series analysis
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_signals_person_type
    ON email_signals(person_id, signal_type);

CREATE INDEX IF NOT EXISTS idx_email_signals_extracted_at
    ON email_signals(person_id, extracted_at DESC);

-- Comment
COMMENT ON TABLE email_signals IS 'Extracted intelligence signals from email patterns';
COMMENT ON COLUMN email_signals.signal_type IS 'subscription, avoidance, boundary_erosion, cognitive_load';
COMMENT ON COLUMN email_signals.signal_data IS 'Type-specific signal data as JSON';


-- =============================================================================
-- EMAIL_SYNC_PROGRESS TABLE (Optional - for UI progress display)
-- =============================================================================
-- Tracks ongoing sync progress for UI feedback

CREATE TABLE IF NOT EXISTS email_sync_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,

    -- Progress tracking
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, syncing, extracting, complete, error
    current_phase TEXT,  -- 'fetching_ids', 'fetching_metadata', 'extracting_signals'

    -- Counts
    total_messages INTEGER DEFAULT 0,
    messages_synced INTEGER DEFAULT 0,
    messages_per_second FLOAT,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Error tracking
    error TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(person_id, provider)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_email_sync_progress_person
    ON email_sync_progress(person_id);

-- Comment
COMMENT ON TABLE email_sync_progress IS 'Real-time sync progress for UI feedback';


-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_email_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for email_sync_state
DROP TRIGGER IF EXISTS trg_email_sync_state_updated_at ON email_sync_state;
CREATE TRIGGER trg_email_sync_state_updated_at
    BEFORE UPDATE ON email_sync_state
    FOR EACH ROW
    EXECUTE FUNCTION update_email_updated_at();

-- Trigger for email_sync_progress
DROP TRIGGER IF EXISTS trg_email_sync_progress_updated_at ON email_sync_progress;
CREATE TRIGGER trg_email_sync_progress_updated_at
    BEFORE UPDATE ON email_sync_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_email_updated_at();


-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================
-- Ensure users can only access their own email data

ALTER TABLE email_sync_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_sync_progress ENABLE ROW LEVEL SECURITY;

-- Policies (idempotent: drop + create)
DROP POLICY IF EXISTS email_sync_state_user_policy ON email_sync_state;
CREATE POLICY email_sync_state_user_policy ON email_sync_state
    FOR ALL USING (person_id = auth.uid());

DROP POLICY IF EXISTS email_events_user_policy ON email_events;
CREATE POLICY email_events_user_policy ON email_events
    FOR ALL USING (person_id = auth.uid());

DROP POLICY IF EXISTS email_signals_user_policy ON email_signals;
CREATE POLICY email_signals_user_policy ON email_signals
    FOR ALL USING (person_id = auth.uid());

DROP POLICY IF EXISTS email_sync_progress_user_policy ON email_sync_progress;
CREATE POLICY email_sync_progress_user_policy ON email_sync_progress
    FOR ALL USING (person_id = auth.uid());


-- =============================================================================
-- ROLLBACK SCRIPT (for reference)
-- =============================================================================
-- To rollback this migration:
--
-- DROP POLICY IF EXISTS email_sync_state_user_policy ON email_sync_state;
-- DROP POLICY IF EXISTS email_events_user_policy ON email_events;
-- DROP POLICY IF EXISTS email_signals_user_policy ON email_signals;
-- DROP POLICY IF EXISTS email_sync_progress_user_policy ON email_sync_progress;
--
-- DROP TABLE IF EXISTS email_sync_progress;
-- DROP TABLE IF EXISTS email_signals;
-- DROP TABLE IF EXISTS email_events;
-- DROP TABLE IF EXISTS email_sync_state;
--
-- DROP FUNCTION IF EXISTS update_email_updated_at();

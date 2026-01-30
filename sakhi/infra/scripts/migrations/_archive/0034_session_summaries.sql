-- Migration: 0034_session_summaries
-- Purpose: Create session_summaries table for compressed conversation context
-- Date: 2026-01-26

-- Table to store compressed older conversation context
CREATE TABLE IF NOT EXISTS session_summaries (
    session_id UUID PRIMARY KEY REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    turn_count_at_summary INT  -- Track how many turns were summarized
);

-- Index fo r fast lookups
CREATE INDEX IF NOT EXISTS idx_session_summaries_updated
    ON session_summaries(last_updated DESC);

COMMENT ON TABLE session_summaries IS
'Compressed context from older conversation turns. Used for hybrid context management: recent turns verbatim + older turns summarized.';

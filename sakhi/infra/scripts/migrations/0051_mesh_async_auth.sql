-- Mesh Async & Auth Enhancement Tables
-- Adds support for:
-- 1. Private key storage for JWT signing
-- 2. Enhanced message queue with retry tracking
-- 3. Response correlation

-- Private key storage (encrypted)
CREATE TABLE IF NOT EXISTS mesh_private_keys (
    sakhi_id TEXT PRIMARY KEY,
    encrypted_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    rotated_at TIMESTAMPTZ
);

-- Response correlation for linking responses to requests
CREATE TABLE IF NOT EXISTS mesh_response_correlation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_message_id TEXT NOT NULL,
    response_message_id TEXT NOT NULL,
    correlated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(request_message_id, response_message_id)
);

CREATE INDEX IF NOT EXISTS idx_correlation_request ON mesh_response_correlation(request_message_id);
CREATE INDEX IF NOT EXISTS idx_correlation_response ON mesh_response_correlation(response_message_id);

-- Add columns to mesh_message_queue if they don't exist
DO $$
BEGIN
    -- Add max_retries column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'mesh_message_queue' AND column_name = 'max_retries'
    ) THEN
        ALTER TABLE mesh_message_queue ADD COLUMN max_retries INT DEFAULT 5;
    END IF;

    -- Add next_retry_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'mesh_message_queue' AND column_name = 'next_retry_at'
    ) THEN
        ALTER TABLE mesh_message_queue ADD COLUMN next_retry_at TIMESTAMPTZ;
    END IF;

    -- Add status column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'mesh_message_queue' AND column_name = 'status'
    ) THEN
        ALTER TABLE mesh_message_queue ADD COLUMN status TEXT DEFAULT 'pending';
    END IF;

    -- Add error_message column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'mesh_message_queue' AND column_name = 'error_message'
    ) THEN
        ALTER TABLE mesh_message_queue ADD COLUMN error_message TEXT;
    END IF;

    -- Add response_received_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'mesh_message_queue' AND column_name = 'response_received_at'
    ) THEN
        ALTER TABLE mesh_message_queue ADD COLUMN response_received_at TIMESTAMPTZ;
    END IF;

    -- Add response_payload column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'mesh_message_queue' AND column_name = 'response_payload'
    ) THEN
        ALTER TABLE mesh_message_queue ADD COLUMN response_payload JSONB;
    END IF;
END $$;

-- Index for pending messages ready for retry
CREATE INDEX IF NOT EXISTS idx_mesh_queue_pending_retry
ON mesh_message_queue(to_sakhi_id, status, next_retry_at)
WHERE status = 'pending';

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_mesh_queue_status ON mesh_message_queue(status);

-- Add sakhi_handle column to sakhi_entities if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sakhi_entities' AND column_name = 'sakhi_handle'
    ) THEN
        ALTER TABLE sakhi_entities ADD COLUMN sakhi_handle TEXT;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_sakhi_entities_handle ON sakhi_entities(LOWER(sakhi_handle)) WHERE sakhi_handle IS NOT NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sakhi_entities' AND column_name = 'bio'
    ) THEN
        ALTER TABLE sakhi_entities ADD COLUMN bio TEXT;
    END IF;
END $$;

-- Full-text search index on sakhi_entities for discovery
CREATE INDEX IF NOT EXISTS idx_sakhi_entities_search
ON sakhi_entities USING gin(to_tsvector('english', COALESCE(display_name, '') || ' ' || COALESCE(sakhi_handle, '') || ' ' || COALESCE(bio, '')));

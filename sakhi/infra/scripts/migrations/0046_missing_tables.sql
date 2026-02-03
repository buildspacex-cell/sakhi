-- Migration 0046: Missing Tables
-- Date: 2026-02-01
--
-- Creates tables that are referenced by code but don't exist:
-- 1. sensory_preferences - Deep sensory preference tracking
-- 2. scheduling_requests - Calendar scheduling request management
-- 3. session_summaries (column) - Add turn_count_at_summary if missing
-- 4. device_link_codes - Device linking flow for desktop agent
-- 5. Ensure agent tables from 0044/0045 exist

-- =============================================================================
-- SENSORY PREFERENCES TABLE
-- =============================================================================
-- Tracks HOW someone likes things: temperature, texture, spice, etc.
-- This is what makes Sakhi truly "know you"

CREATE TABLE IF NOT EXISTS sensory_preferences (
    person_id UUID PRIMARY KEY,

    -- Sensory categories (JSONB for flexibility)
    temperature JSONB DEFAULT '{}',   -- e.g., {"drinks_hot": {"value": true, "strength": "strong"}}
    texture JSONB DEFAULT '{}',       -- e.g., {"prefer_crunchy": {"value": true}}
    spice JSONB DEFAULT '{}',         -- e.g., {"tolerance": {"value": "medium"}}
    flavor JSONB DEFAULT '{}',        -- e.g., {"sweet_preference": {"value": "moderate"}}
    visual JSONB DEFAULT '{}',        -- e.g., {"plating_preference": {"value": "artistic"}}
    ambiance JSONB DEFAULT '{}',      -- e.g., {"noise_level": {"value": "quiet"}}
    portion JSONB DEFAULT '{}',       -- e.g., {"size_preference": {"value": "moderate"}}
    service JSONB DEFAULT '{}',       -- e.g., {"style": {"value": "attentive"}}

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE sensory_preferences IS 'Deep sensory preferences for how someone experiences things - temperature, texture, spice, ambiance, etc.';

-- =============================================================================
-- SCHEDULING REQUESTS TABLE
-- =============================================================================
-- Manages multi-step scheduling flow: parsing → options → confirmation → event

CREATE TABLE IF NOT EXISTS scheduling_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- Request info
    original_request TEXT NOT NULL,
    parsed_intent JSONB NOT NULL DEFAULT '{}',

    -- People involved
    related_person_ids UUID[] DEFAULT '{}',

    -- Options presented
    proposed_times JSONB DEFAULT '[]',
    selected_option INT,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'options_presented',
        'confirmed',
        'cancelled',
        'expired'
    )),

    -- Result
    resulting_event_id UUID,
    resolved_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduling_requests_person ON scheduling_requests(person_id);
CREATE INDEX IF NOT EXISTS idx_scheduling_requests_status ON scheduling_requests(person_id, status);
CREATE INDEX IF NOT EXISTS idx_scheduling_requests_pending ON scheduling_requests(person_id, status, created_at)
    WHERE status = 'options_presented';

COMMENT ON TABLE scheduling_requests IS 'Multi-step scheduling requests - tracks from intent parsing through event creation';

-- =============================================================================
-- SESSION SUMMARIES - Add missing column
-- =============================================================================
-- Adds turn_count_at_summary if the column doesn't exist

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_summaries'
        AND column_name = 'turn_count_at_summary'
    ) THEN
        ALTER TABLE session_summaries
        ADD COLUMN turn_count_at_summary INT DEFAULT 0;
    END IF;
END $$;

-- Create the table if it doesn't exist at all
CREATE TABLE IF NOT EXISTS session_summaries (
    session_id UUID PRIMARY KEY,
    summary TEXT,
    turn_count_at_summary INT DEFAULT 0,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- DEVICE LINK CODES TABLE
-- =============================================================================
-- OAuth-style device linking for desktop/mobile agents

CREATE TABLE IF NOT EXISTS device_link_codes (
    code TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,

    -- Device info
    platform TEXT NOT NULL,
    architecture TEXT,
    agent_type TEXT NOT NULL DEFAULT 'desktop',
    agent_name TEXT,

    -- Linking status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'expired', 'used')),
    person_id UUID,  -- Set when user confirms

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '10 minutes',
    confirmed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_device_link_codes_device ON device_link_codes(device_id);
CREATE INDEX IF NOT EXISTS idx_device_link_codes_status ON device_link_codes(status, expires_at);

COMMENT ON TABLE device_link_codes IS 'Temporary codes for linking desktop/mobile agents to user accounts';

-- =============================================================================
-- AGENT APPROVAL REQUESTS TABLE (from 0044)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_approval_requests (
    request_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    person_id UUID NOT NULL,
    action_type TEXT NOT NULL,
    action_parameters JSONB NOT NULL DEFAULT '{}',
    action_description TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'auto_approved')),
    context_summary TEXT,
    why_approval_needed TEXT,
    if_approved TEXT,
    if_rejected TEXT,
    options JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    screenshot_id TEXT,
    screenshot_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_approval_person_id ON agent_approval_requests(person_id);
CREATE INDEX IF NOT EXISTS idx_agent_approval_status ON agent_approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_agent_approval_pending ON agent_approval_requests(person_id, status) WHERE status = 'pending';

-- =============================================================================
-- REGISTERED AGENTS TABLE (from 0045)
-- =============================================================================
CREATE TABLE IF NOT EXISTS registered_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    device_id TEXT NOT NULL,
    agent_version TEXT NOT NULL DEFAULT '1.0.0',
    protocol_version TEXT NOT NULL DEFAULT '1.0',
    platform TEXT NOT NULL,
    platform_version TEXT,
    architecture TEXT,
    capabilities JSONB NOT NULL DEFAULT '[]',
    approved_capabilities JSONB NOT NULL DEFAULT '[]',
    auth_token_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'registered' CHECK (status IN ('registered', 'active', 'idle', 'offline', 'revoked')),
    last_heartbeat_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_registered_agents_person ON registered_agents(person_id);
CREATE INDEX IF NOT EXISTS idx_registered_agents_status ON registered_agents(status);

-- =============================================================================
-- AGENT SESSIONS TABLE (from 0045)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    task_description TEXT,
    task_type TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'failed', 'cancelled', 'timeout')),
    current_step INT DEFAULT 0,
    total_steps INT,
    actions_executed INT DEFAULT 0,
    actions_failed INT DEFAULT 0,
    screen_understanding JSONB,
    last_screenshot_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_person ON agent_sessions(person_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_agent ON agent_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);

-- =============================================================================
-- AGENT TASK PLANS TABLE (from 0045)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_task_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    session_id UUID,
    task_type TEXT NOT NULL,
    task_description TEXT NOT NULL,
    steps JSONB NOT NULL DEFAULT '[]',
    context_used JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'pending_confirmation', 'executing', 'completed', 'failed', 'cancelled')),
    current_step_index INT DEFAULT 0,
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_task_plans_person ON agent_task_plans(person_id);
CREATE INDEX IF NOT EXISTS idx_agent_task_plans_status ON agent_task_plans(person_id, status);

-- =============================================================================
-- AGENT ACTIONS TABLE (from 0045)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    person_id UUID NOT NULL,
    action_type TEXT NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    sequence INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'executing', 'completed', 'failed', 'cancelled')),
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMPTZ,
    approved_by TEXT,
    sent_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_actions_session ON agent_actions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_actions_agent ON agent_actions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_actions_status ON agent_actions(status);

-- =============================================================================
-- AGENT SCREENSHOTS TABLE (from 0045)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_screenshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID,
    agent_id UUID NOT NULL,
    person_id UUID NOT NULL,
    storage_path TEXT NOT NULL,
    storage_bucket TEXT DEFAULT 'screenshots',
    width INT,
    height INT,
    format TEXT DEFAULT 'png',
    trigger TEXT,
    preceding_action_id UUID,
    analysis JSONB,
    analyzed_at TIMESTAMPTZ,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_screenshots_session ON agent_screenshots(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_screenshots_person ON agent_screenshots(person_id);

-- =============================================================================
-- DONE
-- =============================================================================

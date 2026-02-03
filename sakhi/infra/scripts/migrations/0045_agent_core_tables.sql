-- Migration 0045: Agent Core Tables
-- Date: 2026-01-31
--
-- Core tables for the desktop/mobile agent system.
-- Agents are "dumb hands" that capture screen and execute actions.
-- The API is the "smart brain" that understands and plans.
--
-- Architecture:
-- 1. registered_agents: Agent registration and capabilities
-- 2. agent_sessions: Task sessions (user wants to do something)
-- 3. agent_actions: Individual actions in a session
-- 4. agent_screenshots: Screen captures for vision loop
-- 5. agent_versions: Agent software updates

-- =============================================================================
-- REGISTERED AGENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS registered_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- Agent identity
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL,  -- 'desktop', 'mobile', 'browser'
    device_id TEXT NOT NULL,   -- Hashed device identifier

    -- Version info
    agent_version TEXT NOT NULL,
    protocol_version TEXT NOT NULL DEFAULT '1.0',

    -- Platform info
    platform TEXT NOT NULL,  -- 'macos', 'windows', 'linux', 'ios', 'android'
    platform_version TEXT,
    architecture TEXT,  -- 'arm64', 'x86_64'

    -- Capabilities
    capabilities JSONB NOT NULL DEFAULT '[]',
    approved_capabilities JSONB NOT NULL DEFAULT '[]',

    -- Auth
    auth_token_hash TEXT NOT NULL,

    -- Status
    status TEXT NOT NULL DEFAULT 'registered' CHECK (status IN ('registered', 'active', 'idle', 'offline', 'revoked')),
    last_heartbeat_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one agent per device per person
    UNIQUE (person_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_registered_agents_person ON registered_agents(person_id);
CREATE INDEX IF NOT EXISTS idx_registered_agents_status ON registered_agents(status);

COMMENT ON TABLE registered_agents IS 'Registered desktop/mobile agents for a user';
COMMENT ON COLUMN registered_agents.capabilities IS 'JSON array of capabilities agent has: ["screen_capture", "mouse", "keyboard", ...]';
COMMENT ON COLUMN registered_agents.approved_capabilities IS 'Capabilities user has approved for this agent';

-- =============================================================================
-- AGENT SESSIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    agent_id UUID NOT NULL REFERENCES registered_agents(id),

    -- Task info
    task_description TEXT,
    task_type TEXT,  -- 'shopping', 'restaurant', 'navigation', 'general'

    -- Status
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'failed', 'cancelled', 'timeout')),

    -- Progress
    current_step INT DEFAULT 0,
    total_steps INT,
    actions_executed INT DEFAULT 0,
    actions_failed INT DEFAULT 0,

    -- Screen context (last known state)
    screen_understanding JSONB,
    last_screenshot_at TIMESTAMPTZ,

    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_person ON agent_sessions(person_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_agent ON agent_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_active ON agent_sessions(agent_id, status) WHERE status = 'active';

COMMENT ON TABLE agent_sessions IS 'Agent task sessions - one session per task the user wants to accomplish';

-- =============================================================================
-- AGENT ACTIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_sessions(id),
    agent_id UUID NOT NULL REFERENCES registered_agents(id),
    person_id UUID NOT NULL,

    -- Action details
    action_type TEXT NOT NULL,  -- 'click', 'type', 'scroll', 'navigate', etc.
    parameters JSONB NOT NULL DEFAULT '{}',
    description TEXT,

    -- Sequencing
    sequence INT NOT NULL DEFAULT 0,

    -- Status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'executing', 'completed', 'failed', 'cancelled')),

    -- Approval
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMPTZ,
    approved_by TEXT,

    -- Execution
    sent_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB,
    error_message TEXT,
    retry_count INT DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_actions_session ON agent_actions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_actions_agent ON agent_actions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_actions_status ON agent_actions(status);
CREATE INDEX IF NOT EXISTS idx_agent_actions_pending ON agent_actions(agent_id, status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_agent_actions_approval ON agent_actions(person_id, requires_approval, approved_at) WHERE requires_approval = true AND approved_at IS NULL;

COMMENT ON TABLE agent_actions IS 'Individual actions queued for agent execution';

-- =============================================================================
-- AGENT SCREENSHOTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_screenshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES agent_sessions(id),
    agent_id UUID NOT NULL REFERENCES registered_agents(id),
    person_id UUID NOT NULL,

    -- Storage
    storage_path TEXT NOT NULL,
    storage_bucket TEXT DEFAULT 'screenshots',

    -- Image info
    width INT,
    height INT,
    format TEXT DEFAULT 'png',

    -- Context
    trigger TEXT,  -- 'initial', 'action_complete', 'manual', 'periodic'
    preceding_action_id UUID REFERENCES agent_actions(id),

    -- Vision analysis
    analysis JSONB,  -- Claude Vision analysis result
    analyzed_at TIMESTAMPTZ,

    -- Timing
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_screenshots_session ON agent_screenshots(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_screenshots_person ON agent_screenshots(person_id);
CREATE INDEX IF NOT EXISTS idx_agent_screenshots_captured ON agent_screenshots(session_id, captured_at DESC);

COMMENT ON TABLE agent_screenshots IS 'Screenshots captured by agents for vision loop analysis';

-- =============================================================================
-- AGENT VERSIONS TABLE (for updates)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Version identity
    agent_type TEXT NOT NULL,  -- 'desktop', 'mobile', 'browser'
    platform TEXT NOT NULL,     -- 'macos', 'windows', 'linux', 'ios', 'android'
    architecture TEXT,          -- 'arm64', 'x86_64', 'universal'
    version TEXT NOT NULL,

    -- Download info
    download_url TEXT NOT NULL,
    checksum TEXT NOT NULL,      -- SHA256
    file_size_bytes BIGINT,

    -- Release info
    release_notes TEXT,
    min_required_version TEXT,   -- Minimum version that can upgrade
    is_mandatory BOOLEAN DEFAULT FALSE,

    -- Status
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'recalled')),

    -- Timestamps
    released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint per version
    UNIQUE (agent_type, platform, architecture, version)
);

CREATE INDEX IF NOT EXISTS idx_agent_versions_lookup ON agent_versions(agent_type, platform, status);

COMMENT ON TABLE agent_versions IS 'Agent software versions and download info for auto-updates';

-- =============================================================================
-- AGENT TASK PLANS TABLE (from task_orchestrator)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_task_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    session_id UUID REFERENCES agent_sessions(id),

    -- Task info
    task_type TEXT NOT NULL,  -- 'shopping', 'restaurant', 'general'
    task_description TEXT NOT NULL,

    -- Plan details
    steps JSONB NOT NULL DEFAULT '[]',
    context_used JSONB DEFAULT '{}',  -- Preferences, memories used

    -- Execution
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'executing', 'completed', 'failed', 'cancelled')),
    current_step_index INT DEFAULT 0,
    result JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_task_plans_person ON agent_task_plans(person_id);
CREATE INDEX IF NOT EXISTS idx_agent_task_plans_session ON agent_task_plans(session_id);

COMMENT ON TABLE agent_task_plans IS 'Multi-step task plans generated by Claude with preference context';

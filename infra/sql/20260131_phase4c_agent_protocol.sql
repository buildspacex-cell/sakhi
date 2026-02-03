-- =============================================================================
-- Phase 4c: Desktop/Mobile Agent Protocol
-- =============================================================================
-- Enables Sakhi to control user's devices through local agents.
--
-- Architecture:
-- - User controls everything from Sakhi App (single control point)
-- - Local Agent runs on device (captures screen, executes actions)
-- - API provides intelligence (vision, planning, reasoning)
-- - Agent is "dumb hands", API is "smart brain"
--
-- Upgrade Strategy:
-- - Protocol versioning for backward compatibility
-- - Capability negotiation (agent declares what it can do)
-- - Auto-update mechanism with graceful degradation
-- =============================================================================

-- =============================================================================
-- 1. Registered Agents Table
-- =============================================================================
-- Tracks all agents registered to a user's account

CREATE TABLE IF NOT EXISTS registered_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,

    -- Agent identification
    agent_name TEXT NOT NULL,              -- User-friendly name: "My MacBook", "Work PC"
    agent_type TEXT NOT NULL,              -- 'desktop', 'mobile', 'browser_extension'
    device_id TEXT NOT NULL,               -- Unique device identifier (hashed)

    -- Version & capabilities
    agent_version TEXT NOT NULL,           -- "1.0.0", "1.2.3"
    protocol_version TEXT NOT NULL,        -- "1.0", "1.1", "2.0"
    capabilities JSONB DEFAULT '[]',       -- ["screen_capture", "mouse", "keyboard", "file_read"]
    /*
    Capabilities:
    - screen_capture: Can capture screenshots
    - mouse_click: Can simulate mouse clicks
    - mouse_move: Can move mouse cursor
    - keyboard_type: Can simulate typing
    - keyboard_shortcut: Can send keyboard shortcuts
    - scroll: Can scroll windows
    - file_read: Can read files
    - file_write: Can write files
    - app_launch: Can launch applications
    - browser_navigate: Can navigate browser URLs
    - clipboard_read: Can read clipboard
    - clipboard_write: Can write to clipboard
    */

    -- Platform info
    platform TEXT,                         -- 'macos', 'windows', 'linux', 'ios', 'android'
    platform_version TEXT,                 -- "14.0", "11", "22H2"
    architecture TEXT,                     -- 'arm64', 'x86_64'

    -- Connection state
    status TEXT DEFAULT 'registered',      -- 'registered', 'online', 'offline', 'suspended'
    last_heartbeat_at TIMESTAMPTZ,
    last_action_at TIMESTAMPTZ,

    -- Security
    auth_token_hash TEXT,                  -- Hashed authentication token
    approved_at TIMESTAMPTZ,               -- When user approved this agent
    approved_capabilities JSONB DEFAULT '[]', -- User-approved capabilities

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(person_id, device_id)
);

CREATE INDEX idx_agents_person ON registered_agents(person_id);
CREATE INDEX idx_agents_status ON registered_agents(status);
CREATE INDEX idx_agents_type ON registered_agents(agent_type);

-- =============================================================================
-- 2. Agent Sessions Table
-- =============================================================================
-- Active sessions between app, agent, and API

CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    agent_id UUID NOT NULL REFERENCES registered_agents(id) ON DELETE CASCADE,

    -- Session state
    status TEXT DEFAULT 'active',          -- 'active', 'paused', 'completed', 'failed', 'cancelled'

    -- Current task context
    task_description TEXT,                 -- What user asked to do
    task_plan_id UUID,                     -- Reference to task_plans if using planner
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER,

    -- Screen context
    last_screenshot_at TIMESTAMPTZ,
    screen_understanding JSONB DEFAULT '{}',
    /*
    {
        "description": "Browser showing Google Flights",
        "detected_elements": [
            {"type": "button", "text": "Search", "bounds": [100, 200, 180, 240]},
            {"type": "input", "label": "Destination", "bounds": [50, 100, 300, 130]}
        ],
        "current_app": "Chrome",
        "current_url": "https://google.com/flights"
    }
    */

    -- Execution tracking
    actions_executed INTEGER DEFAULT 0,
    actions_failed INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ,                -- Session expires if no activity

    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_agent_sessions_person ON agent_sessions(person_id);
CREATE INDEX idx_agent_sessions_agent ON agent_sessions(agent_id);
CREATE INDEX idx_agent_sessions_status ON agent_sessions(status);

-- =============================================================================
-- 3. Agent Actions Table
-- =============================================================================
-- Individual actions sent to agents for execution

CREATE TABLE IF NOT EXISTS agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES registered_agents(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL,

    -- Action definition
    action_type TEXT NOT NULL,             -- 'click', 'type', 'scroll', 'screenshot', 'wait', etc.
    parameters JSONB NOT NULL DEFAULT '{}',
    /*
    Examples:
    click: {"x": 150, "y": 200, "button": "left"}
    type: {"text": "Hello world", "delay_ms": 50}
    scroll: {"direction": "down", "amount": 300}
    screenshot: {}
    wait: {"ms": 1000}
    key: {"key": "enter"}
    shortcut: {"keys": ["cmd", "c"]}
    navigate: {"url": "https://example.com"}
    */

    -- Execution state
    status TEXT DEFAULT 'pending',         -- 'pending', 'sent', 'executing', 'completed', 'failed', 'cancelled'

    -- Approval (for sensitive actions)
    requires_approval BOOL DEFAULT false,
    approved_at TIMESTAMPTZ,
    approved_by TEXT,                      -- 'user' or 'auto'

    -- Results
    result JSONB DEFAULT '{}',
    /*
    {
        "success": true,
        "screenshot_id": "...",  // If screenshot was taken after
        "error": null
    }
    */
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timing
    queued_at TIMESTAMPTZ DEFAULT now(),
    sent_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Ordering
    sequence INTEGER NOT NULL DEFAULT 0,
    depends_on UUID[],                     -- Actions that must complete first

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_agent_actions_session ON agent_actions(session_id);
CREATE INDEX idx_agent_actions_status ON agent_actions(status);
CREATE INDEX idx_agent_actions_agent ON agent_actions(agent_id);

-- =============================================================================
-- 4. Agent Screenshots Table
-- =============================================================================
-- Screenshots captured by agents for vision understanding

CREATE TABLE IF NOT EXISTS agent_screenshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES agent_sessions(id) ON DELETE SET NULL,
    agent_id UUID NOT NULL REFERENCES registered_agents(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL,

    -- Image data
    storage_path TEXT NOT NULL,            -- Path to stored screenshot
    width INTEGER,
    height INTEGER,
    format TEXT DEFAULT 'png',             -- 'png', 'jpeg'
    file_size_bytes INTEGER,

    -- Vision analysis
    analysis JSONB DEFAULT '{}',
    /*
    {
        "description": "Desktop showing VS Code with Python file open",
        "detected_apps": ["VS Code"],
        "detected_elements": [...],
        "ocr_text": "def hello_world()...",
        "confidence": 0.95
    }
    */

    -- Context
    trigger TEXT,                          -- 'action_result', 'periodic', 'user_request', 'error'
    preceding_action_id UUID REFERENCES agent_actions(id),

    -- Timing
    captured_at TIMESTAMPTZ NOT NULL,
    analyzed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_agent_screenshots_session ON agent_screenshots(session_id);
CREATE INDEX idx_agent_screenshots_agent ON agent_screenshots(agent_id);
CREATE INDEX idx_agent_screenshots_captured ON agent_screenshots(captured_at DESC);

-- =============================================================================
-- 5. Agent Update Manifest
-- =============================================================================
-- Tracks available agent versions for auto-update

CREATE TABLE IF NOT EXISTS agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Version info
    version TEXT NOT NULL,                 -- "1.0.0", "1.2.3"
    protocol_version TEXT NOT NULL,        -- "1.0", "1.1"
    agent_type TEXT NOT NULL,              -- 'desktop', 'mobile', 'browser_extension'
    platform TEXT NOT NULL,                -- 'macos', 'windows', 'linux', etc.
    architecture TEXT,                     -- 'arm64', 'x86_64', 'universal'

    -- Download info
    download_url TEXT NOT NULL,
    checksum TEXT NOT NULL,                -- SHA256 hash
    file_size_bytes INTEGER,

    -- Release info
    release_notes TEXT,
    min_os_version TEXT,                   -- Minimum OS version required

    -- Rollout control
    rollout_percentage INTEGER DEFAULT 100, -- 0-100 for gradual rollout
    is_mandatory BOOL DEFAULT false,       -- Force update if true
    min_required_version TEXT,             -- Minimum version that can use API

    -- Status
    status TEXT DEFAULT 'active',          -- 'active', 'deprecated', 'recalled'

    released_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(version, agent_type, platform, architecture)
);

CREATE INDEX idx_agent_versions_lookup ON agent_versions(agent_type, platform, status);

-- =============================================================================
-- 6. Agent Capabilities Registry
-- =============================================================================
-- Defines all possible agent capabilities and their requirements

CREATE TABLE IF NOT EXISTS agent_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Capability definition
    capability_name TEXT PRIMARY KEY,      -- 'screen_capture', 'mouse_click', etc.
    display_name TEXT NOT NULL,
    description TEXT,
    category TEXT,                         -- 'input', 'output', 'system', 'browser'

    -- Requirements
    requires_approval BOOL DEFAULT false,  -- User must explicitly approve
    risk_level TEXT DEFAULT 'low',         -- 'low', 'medium', 'high'

    -- Protocol version requirements
    min_protocol_version TEXT DEFAULT '1.0',

    -- Platform support
    supported_platforms JSONB DEFAULT '["macos", "windows", "linux"]',

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Insert default capabilities
INSERT INTO agent_capabilities (capability_name, display_name, description, category, requires_approval, risk_level) VALUES
    ('screen_capture', 'Screen Capture', 'Capture screenshots of your screen', 'output', false, 'low'),
    ('mouse_click', 'Mouse Click', 'Click at specific screen locations', 'input', false, 'medium'),
    ('mouse_move', 'Mouse Move', 'Move the mouse cursor', 'input', false, 'low'),
    ('keyboard_type', 'Keyboard Typing', 'Type text using keyboard', 'input', false, 'medium'),
    ('keyboard_shortcut', 'Keyboard Shortcuts', 'Send keyboard shortcuts like Cmd+C', 'input', true, 'medium'),
    ('scroll', 'Scroll', 'Scroll windows up/down', 'input', false, 'low'),
    ('file_read', 'Read Files', 'Read files from your computer', 'system', true, 'high'),
    ('file_write', 'Write Files', 'Write or create files', 'system', true, 'high'),
    ('app_launch', 'Launch Apps', 'Open applications', 'system', false, 'medium'),
    ('browser_navigate', 'Browser Navigation', 'Navigate to URLs in browser', 'browser', false, 'low'),
    ('clipboard_read', 'Read Clipboard', 'Read clipboard contents', 'system', true, 'medium'),
    ('clipboard_write', 'Write Clipboard', 'Copy text to clipboard', 'system', false, 'low')
ON CONFLICT (capability_name) DO NOTHING;

-- =============================================================================
-- 7. Helper Functions
-- =============================================================================

-- Get pending actions for an agent
CREATE OR REPLACE FUNCTION get_pending_agent_actions(
    p_agent_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    action_id UUID,
    action_type TEXT,
    parameters JSONB,
    sequence INTEGER,
    requires_approval BOOL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id as action_id,
        a.action_type,
        a.parameters,
        a.sequence,
        a.requires_approval
    FROM agent_actions a
    JOIN agent_sessions s ON s.id = a.session_id
    WHERE a.agent_id = p_agent_id
      AND a.status = 'pending'
      AND s.status = 'active'
      AND (a.requires_approval = false OR a.approved_at IS NOT NULL)
    ORDER BY a.sequence ASC, a.created_at ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Check if agent needs update
CREATE OR REPLACE FUNCTION check_agent_update(
    p_agent_type TEXT,
    p_platform TEXT,
    p_current_version TEXT,
    p_architecture TEXT DEFAULT NULL
)
RETURNS TABLE (
    has_update BOOL,
    latest_version TEXT,
    download_url TEXT,
    is_mandatory BOOL,
    release_notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.version != p_current_version as has_update,
        v.version as latest_version,
        v.download_url,
        v.is_mandatory,
        v.release_notes
    FROM agent_versions v
    WHERE v.agent_type = p_agent_type
      AND v.platform = p_platform
      AND v.status = 'active'
      AND (p_architecture IS NULL OR v.architecture = p_architecture OR v.architecture = 'universal')
    ORDER BY v.released_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 8. Comments
-- =============================================================================

COMMENT ON TABLE registered_agents IS 'Agents (desktop/mobile) registered to user accounts';
COMMENT ON TABLE agent_sessions IS 'Active sessions for agent-assisted tasks';
COMMENT ON TABLE agent_actions IS 'Individual actions queued for agent execution';
COMMENT ON TABLE agent_screenshots IS 'Screenshots captured by agents for vision understanding';
COMMENT ON TABLE agent_versions IS 'Available agent versions for auto-update';
COMMENT ON TABLE agent_capabilities IS 'Registry of all agent capabilities';

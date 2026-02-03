-- =============================================================================
-- Phase 4b: Agentic Tasks
-- =============================================================================
-- Enables Sakhi to act in the world on behalf of the user.
--
-- Capabilities:
-- - Web search and research
-- - Task planning and execution
-- - Tool invocation with user approval
-- - Result caching and learning
-- =============================================================================

-- =============================================================================
-- 1. Available Tools Registry
-- =============================================================================
-- Tools that Sakhi can use

CREATE TABLE IF NOT EXISTS sakhi_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tool identity
    tool_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'search', 'research', 'utility', 'integration', 'action'

    -- Capabilities
    capabilities JSONB DEFAULT '[]',
    /* Example:
    ["web_search", "get_url", "summarize", "extract_data"]
    */

    -- Parameters schema
    parameters_schema JSONB DEFAULT '{}',
    /* JSON Schema for tool parameters */

    -- Execution
    handler_type TEXT NOT NULL DEFAULT 'internal',  -- 'internal', 'api', 'mcp', 'custom'
    handler_config JSONB DEFAULT '{}',
    /* For API type:
    {
        "base_url": "https://api.example.com",
        "auth_type": "api_key",
        "auth_header": "X-API-Key"
    }
    */

    -- Trust & Safety
    requires_approval BOOLEAN DEFAULT true,  -- User must approve before execution
    approval_level TEXT DEFAULT 'always',    -- 'always', 'first_time', 'never'
    risk_level TEXT DEFAULT 'low',           -- 'low', 'medium', 'high'

    -- Status
    enabled BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Default tools
INSERT INTO sakhi_tools (tool_name, display_name, description, category, capabilities, requires_approval, approval_level, risk_level)
VALUES
    ('web_search', 'Web Search', 'Search the web for information', 'search',
     '["search", "find_information"]', false, 'never', 'low'),
    ('fetch_url', 'Fetch URL', 'Get content from a URL', 'research',
     '["get_url", "read_webpage"]', false, 'never', 'low'),
    ('summarize', 'Summarize', 'Summarize long content', 'utility',
     '["summarize", "condense"]', false, 'never', 'low'),
    ('weather', 'Weather', 'Get current weather and forecast', 'integration',
     '["get_weather", "forecast"]', false, 'never', 'low'),
    ('calculate', 'Calculate', 'Perform calculations', 'utility',
     '["math", "calculate", "convert"]', false, 'never', 'low')
ON CONFLICT (tool_name) DO NOTHING;

CREATE INDEX idx_tools_category ON sakhi_tools(category);
CREATE INDEX idx_tools_enabled ON sakhi_tools(enabled);

-- =============================================================================
-- 2. User Tool Permissions
-- =============================================================================
-- Per-user tool permissions and preferences

CREATE TABLE IF NOT EXISTS user_tool_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    tool_id UUID NOT NULL REFERENCES sakhi_tools(id) ON DELETE CASCADE,

    -- Permission
    permission TEXT DEFAULT 'ask',  -- 'allow', 'ask', 'deny'
    auto_approve BOOLEAN DEFAULT false,

    -- Usage tracking
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- User preferences for this tool
    preferences JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(person_id, tool_id)
);

CREATE INDEX idx_user_tools_person ON user_tool_permissions(person_id);

-- =============================================================================
-- 3. Task Plans
-- =============================================================================
-- Multi-step task planning

CREATE TABLE IF NOT EXISTS task_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    session_id TEXT,

    -- Task info
    task_description TEXT NOT NULL,
    goal TEXT NOT NULL,

    -- Planning
    steps JSONB DEFAULT '[]',
    /* Example:
    [
        {"step": 1, "action": "web_search", "query": "best restaurants downtown", "status": "pending"},
        {"step": 2, "action": "summarize", "input": "step_1_results", "status": "pending"},
        {"step": 3, "action": "respond", "content": "summary", "status": "pending"}
    ]
    */

    current_step INTEGER DEFAULT 0,

    -- Status
    status TEXT DEFAULT 'planning',  -- 'planning', 'pending_approval', 'executing', 'paused', 'completed', 'failed', 'cancelled'

    -- Results
    results JSONB DEFAULT '{}',
    final_output TEXT,

    -- Execution context
    context JSONB DEFAULT '{}',

    -- Timestamps
    planned_at TIMESTAMPTZ DEFAULT now(),
    approved_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_task_plans_person ON task_plans(person_id);
CREATE INDEX idx_task_plans_status ON task_plans(status);
CREATE INDEX idx_task_plans_session ON task_plans(session_id);

-- =============================================================================
-- 4. Tool Executions
-- =============================================================================
-- Record of every tool execution

CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    tool_id UUID REFERENCES sakhi_tools(id),
    task_plan_id UUID REFERENCES task_plans(id),

    -- What was executed
    tool_name TEXT NOT NULL,
    parameters JSONB DEFAULT '{}',

    -- Approval
    required_approval BOOLEAN DEFAULT false,
    approved BOOLEAN,
    approved_at TIMESTAMPTZ,

    -- Execution
    status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'executing', 'completed', 'failed', 'denied'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Results
    result JSONB,
    result_summary TEXT,
    error TEXT,

    -- Learning
    was_helpful BOOLEAN,  -- User feedback

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tool_exec_person ON tool_executions(person_id);
CREATE INDEX idx_tool_exec_tool ON tool_executions(tool_name);
CREATE INDEX idx_tool_exec_status ON tool_executions(status);
CREATE INDEX idx_tool_exec_plan ON tool_executions(task_plan_id);

-- =============================================================================
-- 5. Search Results Cache
-- =============================================================================
-- Cache web search results to avoid redundant queries

CREATE TABLE IF NOT EXISTS search_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Query
    query_hash TEXT NOT NULL,  -- Hash of normalized query
    query_text TEXT NOT NULL,
    search_engine TEXT DEFAULT 'web',  -- 'web', 'news', 'images', 'local'

    -- Results
    results JSONB NOT NULL,
    result_count INTEGER,

    -- Metadata
    searched_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '1 hour',

    -- Usage
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX idx_search_cache_hash ON search_cache(query_hash);
CREATE INDEX idx_search_cache_expires ON search_cache(expires_at);

-- =============================================================================
-- 6. Research Sessions
-- =============================================================================
-- For multi-turn research tasks

CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,

    -- Research topic
    topic TEXT NOT NULL,
    question TEXT,

    -- Sources gathered
    sources JSONB DEFAULT '[]',
    /* Example:
    [
        {"url": "...", "title": "...", "summary": "...", "relevance": 0.9},
        {"url": "...", "title": "...", "summary": "...", "relevance": 0.7}
    ]
    */

    -- Findings
    findings JSONB DEFAULT '[]',
    synthesis TEXT,

    -- Status
    status TEXT DEFAULT 'active',  -- 'active', 'paused', 'completed'

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_research_person ON research_sessions(person_id);
CREATE INDEX idx_research_status ON research_sessions(status);

-- =============================================================================
-- 7. Learned Preferences
-- =============================================================================
-- What Sakhi learns about how to help the user

CREATE TABLE IF NOT EXISTS agentic_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,

    -- Preference type
    preference_type TEXT NOT NULL,  -- 'search_style', 'summary_length', 'auto_approve', 'preferred_sources'
    preference_key TEXT NOT NULL,
    preference_value JSONB NOT NULL,

    -- Learning
    confidence FLOAT DEFAULT 0.5,
    times_confirmed INTEGER DEFAULT 1,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(person_id, preference_type, preference_key)
);

CREATE INDEX idx_agentic_prefs_person ON agentic_preferences(person_id);

-- =============================================================================
-- 8. Helper Functions
-- =============================================================================

-- Get available tools for a user
CREATE OR REPLACE FUNCTION get_available_tools(p_person_id TEXT)
RETURNS TABLE (
    tool_name TEXT,
    display_name TEXT,
    description TEXT,
    category TEXT,
    permission TEXT,
    auto_approve BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.tool_name,
        t.display_name,
        t.description,
        t.category,
        COALESCE(p.permission, 'ask') as permission,
        COALESCE(p.auto_approve, false) as auto_approve
    FROM sakhi_tools t
    LEFT JOIN user_tool_permissions p ON p.tool_id = t.id AND p.person_id = p_person_id
    WHERE t.enabled = true
    ORDER BY t.category, t.display_name;
END;
$$ LANGUAGE plpgsql;

-- Check if user can use tool without approval
CREATE OR REPLACE FUNCTION can_auto_execute(p_person_id TEXT, p_tool_name TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_result BOOLEAN;
BEGIN
    SELECT
        CASE
            WHEN t.requires_approval = false THEN true
            WHEN p.auto_approve = true THEN true
            WHEN p.permission = 'allow' THEN true
            ELSE false
        END INTO v_result
    FROM sakhi_tools t
    LEFT JOIN user_tool_permissions p ON p.tool_id = t.id AND p.person_id = p_person_id
    WHERE t.tool_name = p_tool_name AND t.enabled = true;

    RETURN COALESCE(v_result, false);
END;
$$ LANGUAGE plpgsql;

-- Get cached search results
CREATE OR REPLACE FUNCTION get_cached_search(p_query_hash TEXT)
RETURNS JSONB AS $$
DECLARE
    v_results JSONB;
BEGIN
    UPDATE search_cache
    SET hit_count = hit_count + 1
    WHERE query_hash = p_query_hash
      AND expires_at > now()
    RETURNING results INTO v_results;

    RETURN v_results;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 9. Comments
-- =============================================================================

COMMENT ON TABLE sakhi_tools IS 'Registry of tools Sakhi can use';
COMMENT ON TABLE user_tool_permissions IS 'Per-user tool permissions';
COMMENT ON TABLE task_plans IS 'Multi-step task execution plans';
COMMENT ON TABLE tool_executions IS 'Log of tool invocations';
COMMENT ON TABLE search_cache IS 'Cached search results';
COMMENT ON TABLE research_sessions IS 'Multi-turn research sessions';
COMMENT ON TABLE agentic_preferences IS 'Learned user preferences for agentic behavior';

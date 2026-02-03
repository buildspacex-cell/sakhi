-- Migration 0044: Agent Approval Requests
-- Date: 2026-01-31
--
-- Stores approval requests for high-risk actions in the vision loop.
-- When the agent detects a critical action (purchase, delete, post),
-- it pauses and waits for user confirmation via this table.
--
-- Flow:
-- 1. Vision loop detects high-risk action
-- 2. Creates approval request with status 'pending'
-- 3. Chat interface polls for pending approvals
-- 4. User approves/rejects via chat
-- 5. Vision loop resumes or cancels

-- =============================================================================
-- AGENT APPROVAL REQUESTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_approval_requests (
    -- Primary key
    request_id TEXT PRIMARY KEY,

    -- Session context
    session_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    person_id UUID NOT NULL,

    -- Action details
    action_type TEXT NOT NULL,
    action_parameters JSONB NOT NULL DEFAULT '{}',
    action_description TEXT NOT NULL,

    -- Risk classification
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'auto_approved')),

    -- Context for user decision
    context_summary TEXT,
    why_approval_needed TEXT,
    if_approved TEXT,
    if_rejected TEXT,
    options JSONB DEFAULT '[]',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,  -- 'user', 'timeout', 'auto'

    -- Screenshot for context
    screenshot_id TEXT,
    screenshot_url TEXT
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_agent_approval_person_id ON agent_approval_requests(person_id);
CREATE INDEX IF NOT EXISTS idx_agent_approval_session_id ON agent_approval_requests(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_approval_status ON agent_approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_agent_approval_pending ON agent_approval_requests(person_id, status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_agent_approval_created_at ON agent_approval_requests(created_at DESC);

COMMENT ON TABLE agent_approval_requests IS 'Approval requests for high-risk agent actions (purchase, delete, post). Vision loop pauses until user approves.';
COMMENT ON COLUMN agent_approval_requests.risk_level IS 'low=safe browsing, medium=reversible, high=commits user, critical=irreversible/financial';
COMMENT ON COLUMN agent_approval_requests.options IS 'JSON array of options presented to user: [{label: "Yes", value: "approve"}, ...]';

-- =============================================================================
-- AGENT APPROVAL HISTORY (for analytics and learning)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_approval_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- What was requested
    action_type TEXT NOT NULL,
    risk_level TEXT NOT NULL,

    -- What user decided
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'expired')),
    selected_option TEXT,
    user_comment TEXT,

    -- Timing
    request_created_at TIMESTAMPTZ NOT NULL,
    decision_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    response_time_seconds FLOAT,

    -- Context
    task_type TEXT,
    context_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_approval_history_person ON agent_approval_history(person_id);
CREATE INDEX IF NOT EXISTS idx_agent_approval_history_action ON agent_approval_history(person_id, action_type);

COMMENT ON TABLE agent_approval_history IS 'Historical record of approval decisions for learning user preferences';

-- =============================================================================
-- AGENT USER APPROVAL PREFERENCES
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_approval_preferences (
    person_id UUID PRIMARY KEY,

    -- Auto-approve settings
    auto_approve_actions TEXT[] DEFAULT '{}',  -- Action types user has pre-approved
    approve_medium_risk BOOLEAN DEFAULT FALSE,

    -- Notification preferences
    notify_on_critical BOOLEAN DEFAULT TRUE,
    notification_channel TEXT DEFAULT 'chat',  -- 'chat', 'push', 'email'

    -- Timeouts
    default_timeout_seconds INT DEFAULT 300,  -- 5 minutes

    -- Learning
    learn_from_history BOOLEAN DEFAULT TRUE,  -- Auto-approve based on history

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE agent_approval_preferences IS 'User preferences for action approvals - which actions to auto-approve, timeouts, etc.';

-- Phase 3: Sakhi-to-Sakhi Mesh
-- Database schema for mesh coordination between Sakhi instances

-- =============================================================================
-- SAKHI REGISTRY
-- Each Sakhi instance registers itself to participate in the mesh
-- =============================================================================

CREATE TABLE IF NOT EXISTS sakhi_registry (
    sakhi_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES personal_model(person_id),

    -- Display info
    display_name TEXT NOT NULL,
    avatar_url TEXT,

    -- Mesh connectivity
    endpoint_url TEXT,  -- For direct communication (future)
    public_key TEXT,    -- For message verification (future)

    -- Capabilities
    mesh_enabled BOOLEAN DEFAULT true,
    capabilities JSONB DEFAULT '["scheduling"]'::jsonb,

    -- Privacy settings
    discoverable BOOLEAN DEFAULT false,  -- Can others find this Sakhi?
    share_availability BOOLEAN DEFAULT true,  -- Share availability windows?
    share_preferences BOOLEAN DEFAULT false,  -- Share scheduling preferences?

    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(person_id)  -- One Sakhi per person
);

-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_sakhi_registry_person ON sakhi_registry(person_id);
CREATE INDEX IF NOT EXISTS idx_sakhi_registry_status ON sakhi_registry(status) WHERE status = 'active';

-- =============================================================================
-- SAKHI CONNECTIONS
-- Track which Sakhis can communicate (trust relationships)
-- =============================================================================

CREATE TABLE IF NOT EXISTS sakhi_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- The two Sakhis
    from_sakhi_id UUID NOT NULL REFERENCES sakhi_registry(sakhi_id),
    to_sakhi_id UUID NOT NULL REFERENCES sakhi_registry(sakhi_id),

    -- Connection status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'blocked')),

    -- Permissions (what can they request?)
    can_request_scheduling BOOLEAN DEFAULT true,
    can_see_availability BOOLEAN DEFAULT true,
    can_see_preferences BOOLEAN DEFAULT false,

    -- Metadata
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(from_sakhi_id, to_sakhi_id)
);

-- Index for connection lookups
CREATE INDEX IF NOT EXISTS idx_sakhi_connections_from ON sakhi_connections(from_sakhi_id);
CREATE INDEX IF NOT EXISTS idx_sakhi_connections_to ON sakhi_connections(to_sakhi_id);

-- =============================================================================
-- MESH MESSAGES
-- All messages between Sakhis (for audit and replay)
-- =============================================================================

CREATE TABLE IF NOT EXISTS mesh_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Routing
    from_sakhi_id UUID NOT NULL REFERENCES sakhi_registry(sakhi_id),
    to_sakhi_id UUID NOT NULL REFERENCES sakhi_registry(sakhi_id),

    -- Message content
    message_type TEXT NOT NULL CHECK (message_type IN (
        'scheduling_request',
        'availability_response',
        'proposal',
        'proposal_response',
        'confirmation',
        'cancellation',
        'ping',
        'pong'
    )),
    payload JSONB NOT NULL,

    -- Correlation
    conversation_id UUID,  -- Groups related messages
    in_reply_to UUID REFERENCES mesh_messages(id),

    -- Status
    status TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'delivered', 'read', 'processed', 'failed')),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ
);

-- Indexes for message queries
CREATE INDEX IF NOT EXISTS idx_mesh_messages_from ON mesh_messages(from_sakhi_id);
CREATE INDEX IF NOT EXISTS idx_mesh_messages_to ON mesh_messages(to_sakhi_id);
CREATE INDEX IF NOT EXISTS idx_mesh_messages_conversation ON mesh_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_mesh_messages_pending ON mesh_messages(to_sakhi_id, status) WHERE status = 'sent';

-- =============================================================================
-- COORDINATION REQUESTS
-- Active scheduling coordination between Sakhis
-- =============================================================================

CREATE TABLE IF NOT EXISTS mesh_coordination (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL UNIQUE,  -- Links to mesh_messages

    -- Participants
    initiator_sakhi_id UUID NOT NULL REFERENCES sakhi_registry(sakhi_id),
    target_sakhi_id UUID NOT NULL REFERENCES sakhi_registry(sakhi_id),

    -- What are we coordinating?
    coordination_type TEXT NOT NULL DEFAULT 'scheduling',
    event_type TEXT,  -- 'dinner', 'coffee', 'call', 'meeting'

    -- Request details
    request_context TEXT,  -- "Alice wants to catch up"
    timeframe_start TIMESTAMPTZ,
    timeframe_end TIMESTAMPTZ,
    preferred_duration_minutes INT,

    -- Current state
    status TEXT DEFAULT 'requested' CHECK (status IN (
        'requested',      -- Initial request sent
        'availability_shared',  -- Both shared availability
        'proposed',       -- Time proposed
        'accepted',       -- Both accepted
        'confirmed',      -- Calendar events created
        'declined',       -- One party declined
        'expired',        -- No response in time
        'cancelled'       -- Cancelled by initiator
    )),

    -- Availability windows (collected from both sides)
    initiator_availability JSONB,  -- [{start, end, quality}]
    target_availability JSONB,

    -- The proposal
    proposed_time TIMESTAMPTZ,
    proposed_location TEXT,
    proposed_location_data JSONB,
    proposal_reasoning TEXT,  -- "Both free, mutual preference for Italian"

    -- Response tracking
    initiator_response TEXT CHECK (initiator_response IN ('pending', 'accepted', 'declined')),
    target_response TEXT CHECK (target_response IN ('pending', 'accepted', 'declined')),

    -- Created events
    initiator_event_id UUID,
    target_event_id UUID,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

-- Indexes for coordination queries
CREATE INDEX IF NOT EXISTS idx_mesh_coordination_initiator ON mesh_coordination(initiator_sakhi_id);
CREATE INDEX IF NOT EXISTS idx_mesh_coordination_target ON mesh_coordination(target_sakhi_id);
CREATE INDEX IF NOT EXISTS idx_mesh_coordination_status ON mesh_coordination(status) WHERE status NOT IN ('confirmed', 'declined', 'expired', 'cancelled');

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Get Sakhi by person_id
CREATE OR REPLACE FUNCTION get_sakhi_by_person(p_person_id UUID)
RETURNS TABLE(
    sakhi_id UUID,
    display_name TEXT,
    mesh_enabled BOOLEAN,
    share_availability BOOLEAN,
    share_preferences BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sr.sakhi_id,
        sr.display_name,
        sr.mesh_enabled,
        sr.share_availability,
        sr.share_preferences
    FROM sakhi_registry sr
    WHERE sr.person_id = p_person_id
    AND sr.status = 'active';
END;
$$ LANGUAGE plpgsql;

-- Check if two Sakhis can communicate
CREATE OR REPLACE FUNCTION can_sakhis_communicate(sakhi_a UUID, sakhi_b UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM sakhi_connections
        WHERE (
            (from_sakhi_id = sakhi_a AND to_sakhi_id = sakhi_b)
            OR (from_sakhi_id = sakhi_b AND to_sakhi_id = sakhi_a)
        )
        AND status = 'accepted'
    );
END;
$$ LANGUAGE plpgsql;

-- Get pending messages for a Sakhi
CREATE OR REPLACE FUNCTION get_pending_mesh_messages(p_sakhi_id UUID)
RETURNS TABLE(
    id UUID,
    from_sakhi_id UUID,
    from_display_name TEXT,
    message_type TEXT,
    payload JSONB,
    conversation_id UUID,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mm.id,
        mm.from_sakhi_id,
        sr.display_name as from_display_name,
        mm.message_type,
        mm.payload,
        mm.conversation_id,
        mm.created_at
    FROM mesh_messages mm
    JOIN sakhi_registry sr ON sr.sakhi_id = mm.from_sakhi_id
    WHERE mm.to_sakhi_id = p_sakhi_id
    AND mm.status = 'sent'
    ORDER BY mm.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Get active coordinations for a person
CREATE OR REPLACE FUNCTION get_active_coordinations(p_person_id UUID)
RETURNS TABLE(
    coordination_id UUID,
    role TEXT,
    other_person_name TEXT,
    event_type TEXT,
    status TEXT,
    proposed_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_sakhi_id UUID;
BEGIN
    -- Get this person's Sakhi
    SELECT sakhi_id INTO v_sakhi_id
    FROM sakhi_registry
    WHERE person_id = p_person_id AND status = 'active';

    IF v_sakhi_id IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT
        mc.id as coordination_id,
        CASE
            WHEN mc.initiator_sakhi_id = v_sakhi_id THEN 'initiator'
            ELSE 'target'
        END as role,
        CASE
            WHEN mc.initiator_sakhi_id = v_sakhi_id THEN target_sr.display_name
            ELSE initiator_sr.display_name
        END as other_person_name,
        mc.event_type,
        mc.status,
        mc.proposed_time,
        mc.created_at
    FROM mesh_coordination mc
    JOIN sakhi_registry initiator_sr ON initiator_sr.sakhi_id = mc.initiator_sakhi_id
    JOIN sakhi_registry target_sr ON target_sr.sakhi_id = mc.target_sakhi_id
    WHERE (mc.initiator_sakhi_id = v_sakhi_id OR mc.target_sakhi_id = v_sakhi_id)
    AND mc.status NOT IN ('confirmed', 'declined', 'expired', 'cancelled')
    ORDER BY mc.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Update timestamps
CREATE OR REPLACE FUNCTION update_mesh_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sakhi_registry_updated
    BEFORE UPDATE ON sakhi_registry
    FOR EACH ROW EXECUTE FUNCTION update_mesh_timestamp();

CREATE TRIGGER trg_mesh_coordination_updated
    BEFORE UPDATE ON mesh_coordination
    FOR EACH ROW EXECUTE FUNCTION update_mesh_timestamp();

-- =============================================================================
-- SEED: Auto-register existing users' Sakhis
-- =============================================================================

-- This creates a Sakhi entry for each existing person
INSERT INTO sakhi_registry (person_id, display_name, mesh_enabled)
SELECT
    person_id,
    COALESCE(full_name, 'Sakhi User'),
    true
FROM personal_model
WHERE person_id NOT IN (SELECT person_id FROM sakhi_registry)
ON CONFLICT (person_id) DO NOTHING;

COMMENT ON TABLE sakhi_registry IS 'Registry of all Sakhi instances in the mesh';
COMMENT ON TABLE sakhi_connections IS 'Trust relationships between Sakhis';
COMMENT ON TABLE mesh_messages IS 'All messages exchanged between Sakhis';
COMMENT ON TABLE mesh_coordination IS 'Active coordination sessions (scheduling, etc.)';

-- Inter-Sakhi Mesh Communication Tables
-- Enables real cross-instance Sakhi-to-Sakhi messaging

-- Sakhi endpoint registry
CREATE TABLE IF NOT EXISTS mesh_endpoints (
    sakhi_id TEXT PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES persons(id),
    endpoint_url TEXT NOT NULL,
    display_name TEXT,
    public_key TEXT,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mesh_endpoints_person ON mesh_endpoints(person_id);

-- Message queue for offline delivery
CREATE TABLE IF NOT EXISTS mesh_message_queue (
    message_id TEXT PRIMARY KEY,
    from_sakhi_id TEXT NOT NULL,
    to_sakhi_id TEXT NOT NULL,
    message_type TEXT NOT NULL,
    payload JSONB DEFAULT '{}',
    reply_to TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_attempt TIMESTAMPTZ,
    attempts INT DEFAULT 0,
    delivered_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_mesh_queue_to ON mesh_message_queue(to_sakhi_id);
CREATE INDEX IF NOT EXISTS idx_mesh_queue_undelivered ON mesh_message_queue(to_sakhi_id) WHERE delivered_at IS NULL;

-- Message history
CREATE TABLE IF NOT EXISTS mesh_messages (
    id SERIAL PRIMARY KEY,
    message_id TEXT UNIQUE NOT NULL,
    from_sakhi_id TEXT NOT NULL,
    to_sakhi_id TEXT NOT NULL,
    message_type TEXT NOT NULL,
    payload JSONB DEFAULT '{}',
    reply_to TEXT,
    received_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mesh_messages_from ON mesh_messages(from_sakhi_id);
CREATE INDEX IF NOT EXISTS idx_mesh_messages_to ON mesh_messages(to_sakhi_id);

-- Symptom log for "Last Time" lookup
CREATE TABLE IF NOT EXISTS symptom_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),
    symptom_type TEXT NOT NULL,
    severity FLOAT DEFAULT 0.5,
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    resolution_time TIMESTAMPTZ,
    interventions_tried JSONB DEFAULT '[]',
    what_helped JSONB DEFAULT '[]',
    what_didnt_help JSONB DEFAULT '[]',
    resolution_summary TEXT,
    related_dosha TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_symptom_log_person ON symptom_log(person_id);
CREATE INDEX IF NOT EXISTS idx_symptom_log_type ON symptom_log(person_id, symptom_type);

-- Intervention outcomes tracking
CREATE TABLE IF NOT EXISTS intervention_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),
    intervention_type TEXT NOT NULL,
    intervention_name TEXT NOT NULL,
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    was_effective BOOLEAN,
    effectiveness_score FLOAT,
    symptom_addressed TEXT,
    related_dosha TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intervention_person ON intervention_outcomes(person_id);
CREATE INDEX IF NOT EXISTS idx_intervention_dosha ON intervention_outcomes(person_id, related_dosha);

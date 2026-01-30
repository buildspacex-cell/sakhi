-- =============================================================================
-- Memory Graph Tables
-- =============================================================================
-- Creates the node-edge structure for cross-entity relationship tracking.
--
-- Purpose:
-- - Track relationships between diverse entities (goals, patterns, activities, time slots)
-- - Enable intelligent context loading by traversing connections
-- - Identify competing/supporting relationships (e.g., two activities competing for morning slot)
--
-- Node Types:
-- - goal: User's stated objectives
-- - pattern: Recurring behaviors/themes (from crystallization)
-- - person: People mentioned in conversations
-- - value: Core values extracted from reflection
-- - theme: Recurring topics
-- - time_slot: Morning, afternoon, evening, night
-- - activity: Specific activities (yoga, work, meditation)
-- - emotion: Emotional states
-- - reflection: Synthesized insights
-- - thought: Individual thoughts
-- - plan: Planned actions
-- - insight: Generated insights
-- - event: Life events
--
-- Edge Relations:
-- - supports: A enables or helps B
-- - blocks: A conflicts with or prevents B
-- - competes_with: A and B compete for the same resource (time, energy)
-- - enables: A makes B possible
-- - relates_to: General connection
-- - influences: A affects B's state
-- - scheduled_for: Activity/goal linked to time_slot
-- - mentions: Conversation mentions entity
-- - crystallized_from: Pattern emerged from repeated occurrences
-- =============================================================================

-- Memory Nodes: Entities in the user's memory graph
CREATE TABLE IF NOT EXISTS memory_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- Node classification
    node_kind TEXT NOT NULL CHECK (
        node_kind IN (
            'goal', 'pattern', 'person', 'value', 'theme',
            'time_slot', 'activity', 'emotion', 'reflection',
            'thought', 'plan', 'insight', 'event'
        )
    ),

    -- Human-readable label (unique per person + kind for deduplication)
    label TEXT NOT NULL,

    -- Flexible metadata (varies by kind)
    -- goal: {priority, deadline, status}
    -- pattern: {frequency, last_seen, evidence_count}
    -- time_slot: {start_hour, end_hour, energy_level}
    -- activity: {category, duration_min, energy_cost}
    data JSONB DEFAULT '{}'::jsonb,

    -- Tracking
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    last_referenced_at TIMESTAMPTZ DEFAULT now(),

    -- Strength/importance (0.0 to 1.0)
    weight FLOAT DEFAULT 0.5,

    -- Prevent duplicate nodes per person (same label + kind = same entity)
    CONSTRAINT memory_nodes_unique_label UNIQUE (person_id, node_kind, label)
);

-- Memory Edges: Relationships between nodes
CREATE TABLE IF NOT EXISTS memory_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- Source and destination nodes
    from_node UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    to_node UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,

    -- Relationship type
    relation TEXT NOT NULL CHECK (
        relation IN (
            'supports', 'blocks', 'competes_with', 'enables',
            'relates_to', 'influences', 'scheduled_for', 'mentions',
            'crystallized_from', 'part_of', 'opposite_of'
        )
    ),

    -- Edge strength (0.0 to 1.0, decayed over time, reinforced on re-occurrence)
    weight FLOAT DEFAULT 0.5,

    -- Evidence/context for why this edge exists
    evidence JSONB DEFAULT '{}'::jsonb,

    -- Tracking
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- How many times this relationship was observed
    occurrence_count INTEGER DEFAULT 1,

    -- Prevent duplicate edges
    CONSTRAINT memory_edges_unique UNIQUE (person_id, from_node, to_node, relation)
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- Find all nodes for a person by kind
CREATE INDEX IF NOT EXISTS idx_memory_nodes_person_kind
ON memory_nodes(person_id, node_kind);

-- Find nodes by label (for lookup/deduplication)
CREATE INDEX IF NOT EXISTS idx_memory_nodes_label
ON memory_nodes(person_id, label);

-- Find edges from/to a node (for traversal)
CREATE INDEX IF NOT EXISTS idx_memory_edges_from
ON memory_edges(person_id, from_node);

CREATE INDEX IF NOT EXISTS idx_memory_edges_to
ON memory_edges(person_id, to_node);

-- Find competing/blocking relationships specifically
CREATE INDEX IF NOT EXISTS idx_memory_edges_conflicts
ON memory_edges(person_id, relation)
WHERE relation IN ('blocks', 'competes_with');

-- Find supporting relationships
CREATE INDEX IF NOT EXISTS idx_memory_edges_supports
ON memory_edges(person_id, relation)
WHERE relation IN ('supports', 'enables');

-- Find recently referenced nodes (for context loading)
CREATE INDEX IF NOT EXISTS idx_memory_nodes_recent
ON memory_nodes(person_id, last_referenced_at DESC);

-- =============================================================================
-- Helper Functions
-- =============================================================================

-- Get or create a node (returns node_id)
CREATE OR REPLACE FUNCTION upsert_memory_node(
    p_person_id UUID,
    p_node_kind TEXT,
    p_label TEXT,
    p_data JSONB DEFAULT '{}'::jsonb,
    p_weight FLOAT DEFAULT 0.5
) RETURNS UUID AS $$
DECLARE
    v_node_id UUID;
BEGIN
    -- Try to find existing node
    SELECT id INTO v_node_id
    FROM memory_nodes
    WHERE person_id = p_person_id
      AND node_kind = p_node_kind
      AND label = p_label;

    IF v_node_id IS NOT NULL THEN
        -- Update existing node
        UPDATE memory_nodes
        SET data = p_data || data,  -- Merge new data into existing
            updated_at = now(),
            last_referenced_at = now(),
            weight = GREATEST(weight, p_weight)  -- Keep higher weight
        WHERE id = v_node_id;
    ELSE
        -- Create new node
        INSERT INTO memory_nodes (person_id, node_kind, label, data, weight)
        VALUES (p_person_id, p_node_kind, p_label, p_data, p_weight)
        RETURNING id INTO v_node_id;
    END IF;

    RETURN v_node_id;
END;
$$ LANGUAGE plpgsql;

-- Upsert edge with exponential moving average for weight
CREATE OR REPLACE FUNCTION upsert_memory_edge(
    p_person_id UUID,
    p_from_node UUID,
    p_to_node UUID,
    p_relation TEXT,
    p_weight FLOAT DEFAULT 0.5,
    p_evidence JSONB DEFAULT '{}'::jsonb
) RETURNS UUID AS $$
DECLARE
    v_edge_id UUID;
    v_prev_weight FLOAT;
BEGIN
    -- Try to find existing edge
    SELECT id, weight INTO v_edge_id, v_prev_weight
    FROM memory_edges
    WHERE person_id = p_person_id
      AND from_node = p_from_node
      AND to_node = p_to_node
      AND relation = p_relation;

    IF v_edge_id IS NOT NULL THEN
        -- Reinforce existing edge (EMA: 70% old + 30% new)
        UPDATE memory_edges
        SET weight = v_prev_weight * 0.7 + p_weight * 0.3,
            updated_at = now(),
            occurrence_count = occurrence_count + 1,
            evidence = evidence || p_evidence
        WHERE id = v_edge_id;
    ELSE
        -- Create new edge
        INSERT INTO memory_edges (person_id, from_node, to_node, relation, weight, evidence)
        VALUES (p_person_id, p_from_node, p_to_node, p_relation, p_weight, p_evidence)
        RETURNING id INTO v_edge_id;
    END IF;

    RETURN v_edge_id;
END;
$$ LANGUAGE plpgsql;

-- Find all entities that compete with a given node
CREATE OR REPLACE FUNCTION find_competing_entities(
    p_person_id UUID,
    p_node_id UUID
) RETURNS TABLE (
    node_id UUID,
    node_kind TEXT,
    label TEXT,
    relation TEXT,
    weight FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mn.id,
        mn.node_kind,
        mn.label,
        me.relation,
        me.weight
    FROM memory_edges me
    JOIN memory_nodes mn ON mn.id = CASE
        WHEN me.from_node = p_node_id THEN me.to_node
        ELSE me.from_node
    END
    WHERE me.person_id = p_person_id
      AND (me.from_node = p_node_id OR me.to_node = p_node_id)
      AND me.relation IN ('competes_with', 'blocks')
    ORDER BY me.weight DESC;
END;
$$ LANGUAGE plpgsql;

-- Find all nodes connected to a given node (1-hop traversal)
CREATE OR REPLACE FUNCTION traverse_memory_graph(
    p_person_id UUID,
    p_node_id UUID,
    p_max_hops INTEGER DEFAULT 1
) RETURNS TABLE (
    node_id UUID,
    node_kind TEXT,
    label TEXT,
    relation TEXT,
    weight FLOAT,
    hop_distance INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE traversal AS (
        -- Base case: direct connections
        SELECT
            CASE
                WHEN me.from_node = p_node_id THEN me.to_node
                ELSE me.from_node
            END AS connected_node,
            me.relation,
            me.weight,
            1 AS distance
        FROM memory_edges me
        WHERE me.person_id = p_person_id
          AND (me.from_node = p_node_id OR me.to_node = p_node_id)

        UNION

        -- Recursive case: follow edges
        SELECT
            CASE
                WHEN me.from_node = t.connected_node THEN me.to_node
                ELSE me.from_node
            END,
            me.relation,
            me.weight * 0.7,  -- Decay weight with distance
            t.distance + 1
        FROM memory_edges me
        JOIN traversal t ON (me.from_node = t.connected_node OR me.to_node = t.connected_node)
        WHERE me.person_id = p_person_id
          AND t.distance < p_max_hops
          AND CASE
                WHEN me.from_node = t.connected_node THEN me.to_node
                ELSE me.from_node
              END != p_node_id  -- Don't loop back
    )
    SELECT DISTINCT
        mn.id,
        mn.node_kind,
        mn.label,
        t.relation,
        t.weight,
        t.distance
    FROM traversal t
    JOIN memory_nodes mn ON mn.id = t.connected_node
    ORDER BY t.distance, t.weight DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Pre-populate Time Slot Nodes (System Nodes)
-- =============================================================================
-- These are universal time slots that activities/goals can be scheduled for.
-- We'll create a function to ensure they exist for each user.

CREATE OR REPLACE FUNCTION ensure_time_slot_nodes(p_person_id UUID) RETURNS void AS $$
BEGIN
    -- Morning (6am - 12pm): Vata time, high creativity, variable energy
    PERFORM upsert_memory_node(
        p_person_id, 'time_slot', 'morning',
        '{"start_hour": 6, "end_hour": 12, "energy_quality": "creative", "dosha_dominant": "vata"}'::jsonb,
        0.8
    );

    -- Afternoon (12pm - 6pm): Pitta time, high productivity, peak energy
    PERFORM upsert_memory_node(
        p_person_id, 'time_slot', 'afternoon',
        '{"start_hour": 12, "end_hour": 18, "energy_quality": "productive", "dosha_dominant": "pitta"}'::jsonb,
        0.8
    );

    -- Evening (6pm - 10pm): Kapha time, winding down, steady energy
    PERFORM upsert_memory_node(
        p_person_id, 'time_slot', 'evening',
        '{"start_hour": 18, "end_hour": 22, "energy_quality": "reflective", "dosha_dominant": "kapha"}'::jsonb,
        0.8
    );

    -- Night (10pm - 6am): Rest time
    PERFORM upsert_memory_node(
        p_person_id, 'time_slot', 'night',
        '{"start_hour": 22, "end_hour": 6, "energy_quality": "restorative", "dosha_dominant": "kapha"}'::jsonb,
        0.8
    );
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Update Triggers
-- =============================================================================

-- Auto-update updated_at on node changes
CREATE OR REPLACE FUNCTION update_memory_node_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_memory_nodes_updated
BEFORE UPDATE ON memory_nodes
FOR EACH ROW EXECUTE FUNCTION update_memory_node_timestamp();

-- Auto-update updated_at on edge changes
CREATE TRIGGER tr_memory_edges_updated
BEFORE UPDATE ON memory_edges
FOR EACH ROW EXECUTE FUNCTION update_memory_node_timestamp();

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE memory_nodes IS 'Entities in the user memory graph - goals, patterns, activities, time slots, etc.';
COMMENT ON TABLE memory_edges IS 'Relationships between memory nodes - supports, blocks, competes_with, etc.';
COMMENT ON FUNCTION upsert_memory_node IS 'Get or create a memory node, merging data if exists';
COMMENT ON FUNCTION upsert_memory_edge IS 'Get or create an edge, reinforcing weight if exists (EMA)';
COMMENT ON FUNCTION find_competing_entities IS 'Find all entities that compete with or block a given node';
COMMENT ON FUNCTION traverse_memory_graph IS 'Multi-hop graph traversal from a starting node';

-- =============================================================================
-- Phase 1.1: Relationship Model Enhancement
-- =============================================================================
-- Enhances the memory graph to support rich relationship tracking for people.
--
-- Purpose:
-- - Track relationships with depth (not just entity mentions)
-- - Enable scheduling-aware relationship context
-- - Support "You haven't seen X in Y weeks" intelligence
-- - Lay groundwork for Sakhi-to-Sakhi coordination
--
-- Changes:
-- 1. Add new edge relation types for relationships
-- 2. Create helper functions for relationship management
-- 3. Create view for relationship summary
-- =============================================================================

-- =============================================================================
-- 1. Add new relation types to memory_edges
-- =============================================================================
-- We need to alter the CHECK constraint to add new relation types

ALTER TABLE memory_edges
DROP CONSTRAINT IF EXISTS memory_edges_relation_check;

ALTER TABLE memory_edges
ADD CONSTRAINT memory_edges_relation_check CHECK (
    relation IN (
        -- Original relations
        'supports', 'blocks', 'competes_with', 'enables',
        'relates_to', 'influences', 'scheduled_for', 'mentions',
        'crystallized_from', 'part_of', 'opposite_of',
        -- New relationship-specific relations
        'knows',              -- User knows this person
        'close_to',           -- Close relationship
        'works_with',         -- Professional relationship
        'family_of',          -- Family relationship
        'met_with',           -- Had a meeting/interaction
        'scheduled_with'      -- Has upcoming event with
    )
);

-- =============================================================================
-- 2. Create relationships table for structured relationship data
-- =============================================================================
-- This complements memory_nodes (which tracks the person entity) with
-- structured relationship metadata that doesn't fit in the data JSONB.

CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- Reference to the memory_node for this person
    -- (memory_nodes.node_kind = 'person' AND memory_nodes.label = person name)
    memory_node_id UUID REFERENCES memory_nodes(id) ON DELETE SET NULL,

    -- Relationship basics
    name TEXT NOT NULL,                    -- "Alex", "Mom", "Dr. Smith"
    relationship_type TEXT NOT NULL CHECK (
        relationship_type IN (
            'close_friend', 'friend', 'acquaintance',
            'family', 'partner', 'colleague', 'mentor',
            'professional', 'service_provider', 'other'
        )
    ),

    -- Relationship strength and frequency
    closeness FLOAT DEFAULT 0.5 CHECK (closeness >= 0 AND closeness <= 1),
    frequency_target TEXT CHECK (
        frequency_target IN ('daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly', 'as_needed')
    ),

    -- Last interaction tracking
    last_seen_at TIMESTAMPTZ,              -- Last in-person
    last_contact_at TIMESTAMPTZ,           -- Last any contact (call, text, etc.)
    last_mentioned_at TIMESTAMPTZ,         -- Last mentioned in journal

    -- Sakhi-to-Sakhi (future)
    their_sakhi_id UUID,                   -- If they have Sakhi

    -- Rich context (JSONB for flexibility)
    context JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "current_situation": "Job transition, stressed lately",
        "relationship_history": "College friend, known 10 years",
        "important_to_know": "Wife is Sarah, two kids (Emma 5, Jake 8)",
        "shared_interests": ["hiking", "film photography", "cooking"],
        "communication_style": "Prefers calls over texts",
        "boundaries": "Don't discuss politics"
    }
    */

    -- Patterns observed
    patterns JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "user_energy_after": "energized",  -- or "drained", "neutral"
        "usual_activities": ["dinner", "hiking"],
        "preferred_times": ["weekend afternoons"],
        "preferred_locations": ["downtown", "their place"],
        "typical_duration": 120,           -- minutes
        "notes": "Always runs 15 min late"
    }
    */

    -- Scheduling preferences for this relationship
    scheduling JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "preferred_days": ["saturday", "sunday"],
        "preferred_times": ["afternoon", "evening"],
        "avoid_times": ["weekday mornings"],
        "typical_activities": ["dinner", "coffee"],
        "location_preferences": ["near downtown"]
    }
    */

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Prevent duplicate relationships
    CONSTRAINT relationships_unique_name UNIQUE (person_id, name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_relationships_person
ON relationships(person_id);

CREATE INDEX IF NOT EXISTS idx_relationships_type
ON relationships(person_id, relationship_type);

CREATE INDEX IF NOT EXISTS idx_relationships_closeness
ON relationships(person_id, closeness DESC);

CREATE INDEX IF NOT EXISTS idx_relationships_last_contact
ON relationships(person_id, last_contact_at DESC NULLS LAST);

-- =============================================================================
-- 3. Helper Functions
-- =============================================================================

-- Get or create a relationship
CREATE OR REPLACE FUNCTION upsert_relationship(
    p_person_id UUID,
    p_name TEXT,
    p_relationship_type TEXT DEFAULT 'acquaintance',
    p_closeness FLOAT DEFAULT 0.5,
    p_context JSONB DEFAULT '{}'::jsonb,
    p_patterns JSONB DEFAULT '{}'::jsonb
) RETURNS UUID AS $$
DECLARE
    v_rel_id UUID;
    v_node_id UUID;
BEGIN
    -- First, ensure there's a memory_node for this person
    SELECT id INTO v_node_id
    FROM memory_nodes
    WHERE person_id = p_person_id
      AND node_kind = 'person'
      AND label = p_name;

    IF v_node_id IS NULL THEN
        INSERT INTO memory_nodes (person_id, node_kind, label, data, weight)
        VALUES (p_person_id, 'person', p_name, '{}'::jsonb, p_closeness)
        RETURNING id INTO v_node_id;
    END IF;

    -- Now upsert the relationship
    INSERT INTO relationships (
        person_id, memory_node_id, name, relationship_type,
        closeness, context, patterns
    )
    VALUES (
        p_person_id, v_node_id, p_name, p_relationship_type,
        p_closeness, p_context, p_patterns
    )
    ON CONFLICT (person_id, name) DO UPDATE SET
        relationship_type = COALESCE(EXCLUDED.relationship_type, relationships.relationship_type),
        closeness = GREATEST(EXCLUDED.closeness, relationships.closeness),
        context = relationships.context || EXCLUDED.context,
        patterns = relationships.patterns || EXCLUDED.patterns,
        updated_at = now()
    RETURNING id INTO v_rel_id;

    RETURN v_rel_id;
END;
$$ LANGUAGE plpgsql;

-- Update last contact/seen timestamps
CREATE OR REPLACE FUNCTION update_relationship_contact(
    p_person_id UUID,
    p_name TEXT,
    p_contact_type TEXT DEFAULT 'contact'  -- 'seen', 'contact', 'mentioned'
) RETURNS void AS $$
BEGIN
    UPDATE relationships
    SET
        last_contact_at = CASE
            WHEN p_contact_type IN ('seen', 'contact') THEN now()
            ELSE last_contact_at
        END,
        last_seen_at = CASE
            WHEN p_contact_type = 'seen' THEN now()
            ELSE last_seen_at
        END,
        last_mentioned_at = CASE
            WHEN p_contact_type = 'mentioned' THEN now()
            ELSE last_mentioned_at
        END,
        updated_at = now()
    WHERE person_id = p_person_id AND name = p_name;
END;
$$ LANGUAGE plpgsql;

-- Get relationships needing attention (not contacted in a while)
CREATE OR REPLACE FUNCTION get_relationships_needing_attention(
    p_person_id UUID,
    p_limit INTEGER DEFAULT 5
) RETURNS TABLE (
    id UUID,
    name TEXT,
    relationship_type TEXT,
    closeness FLOAT,
    last_contact_at TIMESTAMPTZ,
    days_since_contact INTEGER,
    frequency_target TEXT,
    context JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.name,
        r.relationship_type,
        r.closeness,
        r.last_contact_at,
        EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at)))::INTEGER as days_since_contact,
        r.frequency_target,
        r.context
    FROM relationships r
    WHERE r.person_id = p_person_id
      AND r.closeness >= 0.5  -- Focus on closer relationships
    ORDER BY
        -- Prioritize by: closeness * days since contact
        r.closeness * EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at))) DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 4. View for relationship summary
-- =============================================================================

CREATE OR REPLACE VIEW relationship_summary AS
SELECT
    r.person_id,
    r.id as relationship_id,
    r.name,
    r.relationship_type,
    r.closeness,
    r.frequency_target,
    r.last_seen_at,
    r.last_contact_at,
    r.last_mentioned_at,
    EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at)))::INTEGER as days_since_contact,
    r.context->>'current_situation' as current_situation,
    r.context->>'important_to_know' as important_to_know,
    r.patterns->>'user_energy_after' as energy_effect,
    r.patterns->'usual_activities' as usual_activities,
    r.their_sakhi_id IS NOT NULL as has_sakhi
FROM relationships r;

-- =============================================================================
-- 5. Trigger to sync with memory_nodes
-- =============================================================================

-- When relationship is updated, update the memory_node weight
CREATE OR REPLACE FUNCTION sync_relationship_to_memory_node()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the memory_node weight to match closeness
    IF NEW.memory_node_id IS NOT NULL THEN
        UPDATE memory_nodes
        SET
            weight = NEW.closeness,
            data = data || jsonb_build_object(
                'relationship_type', NEW.relationship_type,
                'last_contact_at', NEW.last_contact_at
            ),
            updated_at = now()
        WHERE id = NEW.memory_node_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_relationship_sync
AFTER INSERT OR UPDATE ON relationships
FOR EACH ROW EXECUTE FUNCTION sync_relationship_to_memory_node();

-- =============================================================================
-- 6. Comments
-- =============================================================================

COMMENT ON TABLE relationships IS 'Rich relationship data for people in the user life, complementing memory_nodes';
COMMENT ON FUNCTION upsert_relationship IS 'Create or update a relationship with automatic memory_node creation';
COMMENT ON FUNCTION get_relationships_needing_attention IS 'Find relationships that may need reconnection based on closeness and last contact';
COMMENT ON VIEW relationship_summary IS 'Convenience view for relationship data with computed fields';

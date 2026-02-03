-- =============================================================================
-- Phase 1.4: Recommendation Feedback Schema
-- =============================================================================
-- Tracks user feedback on recommendations to improve personalization.
--
-- Purpose:
-- - Record whether recommendations were helpful
-- - Learn what works for each user
-- - Improve future recommendations
-- =============================================================================

-- =============================================================================
-- 1. Recommendation Feedback Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS recommendation_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- What was recommended
    item_name TEXT NOT NULL,              -- e.g., 'warm_milk', 'morning_walk'
    item_type TEXT NOT NULL,              -- 'food', 'practice', 'immediate_action'

    -- Feedback
    helpful BOOLEAN,                      -- True = helpful, False = not helpful, NULL = no feedback
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),  -- Optional 1-5 star rating
    notes TEXT,                           -- Optional user notes

    -- Context when recommended
    friction_state TEXT,                  -- What state they were in
    season TEXT,                          -- Season when recommended
    time_of_day TEXT,                     -- Time when recommended

    -- Tracking
    recommended_at TIMESTAMPTZ DEFAULT now(),
    feedback_at TIMESTAMPTZ,              -- When feedback was provided
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- 2. Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_person ON recommendation_feedback(person_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_item ON recommendation_feedback(item_type, item_name);
CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_helpful ON recommendation_feedback(person_id, helpful);
CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_created ON recommendation_feedback(created_at DESC);

-- =============================================================================
-- 3. Helper Functions
-- =============================================================================

-- Record a recommendation (called when showing recommendations)
CREATE OR REPLACE FUNCTION record_recommendation(
    p_person_id UUID,
    p_item_name TEXT,
    p_item_type TEXT,
    p_friction_state TEXT DEFAULT NULL,
    p_season TEXT DEFAULT NULL,
    p_time_of_day TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO recommendation_feedback (
        person_id, item_name, item_type,
        friction_state, season, time_of_day
    ) VALUES (
        p_person_id, p_item_name, p_item_type,
        p_friction_state, p_season, p_time_of_day
    )
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Record feedback on a recommendation
CREATE OR REPLACE FUNCTION record_recommendation_feedback(
    p_id UUID,
    p_helpful BOOLEAN,
    p_rating INTEGER DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE recommendation_feedback
    SET helpful = p_helpful,
        rating = p_rating,
        notes = p_notes,
        feedback_at = now(),
        updated_at = now()
    WHERE id = p_id;
END;
$$ LANGUAGE plpgsql;

-- Get effective recommendations for a person
CREATE OR REPLACE FUNCTION get_effective_recommendations(
    p_person_id UUID,
    p_item_type TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
) RETURNS TABLE (
    item_name TEXT,
    item_type TEXT,
    helpful_count BIGINT,
    total_count BIGINT,
    effectiveness_rate FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rf.item_name,
        rf.item_type,
        COUNT(*) FILTER (WHERE rf.helpful = TRUE) as helpful_count,
        COUNT(*) as total_count,
        (COUNT(*) FILTER (WHERE rf.helpful = TRUE)::FLOAT / NULLIF(COUNT(*), 0)) as effectiveness_rate
    FROM recommendation_feedback rf
    WHERE rf.person_id = p_person_id
      AND (p_item_type IS NULL OR rf.item_type = p_item_type)
      AND rf.helpful IS NOT NULL
    GROUP BY rf.item_name, rf.item_type
    HAVING COUNT(*) >= 2  -- At least 2 data points
    ORDER BY effectiveness_rate DESC, helpful_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 4. Triggers
-- =============================================================================

CREATE OR REPLACE FUNCTION update_recommendation_feedback_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_recommendation_feedback_updated
BEFORE UPDATE ON recommendation_feedback
FOR EACH ROW EXECUTE FUNCTION update_recommendation_feedback_timestamp();

-- =============================================================================
-- 5. Comments
-- =============================================================================

COMMENT ON TABLE recommendation_feedback IS 'Tracks user feedback on recommendations for personalization';
COMMENT ON FUNCTION get_effective_recommendations IS 'Get recommendations that have been effective for a user';

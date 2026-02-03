-- =============================================================================
-- Phase 1.3: Personal Pattern Learning Schema
-- =============================================================================
-- Stores user-specific cause-effect correlations learned over time.
--
-- Purpose:
-- - Learn personal patterns (when I do X, I feel Y)
-- - Enable personalized "why" explanations
-- - Track correlation strength over observations
-- =============================================================================

-- =============================================================================
-- 1. Personal Patterns Table
-- =============================================================================
-- Stores learned cause-effect relationships for each user

CREATE TABLE IF NOT EXISTS personal_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- The pattern components
    cause_type TEXT NOT NULL,           -- 'behavior', 'food', 'sleep', 'activity', 'environment'
    cause_value TEXT NOT NULL,          -- Normalized cause (e.g., 'late_dinner', 'skipped_exercise')
    effect_type TEXT NOT NULL,          -- 'symptom', 'energy', 'mood', 'friction_state'
    effect_value TEXT NOT NULL,         -- Normalized effect (e.g., 'anxiety', 'low_energy', 'chaos_friction')

    -- Correlation tracking
    observation_count INTEGER DEFAULT 1,        -- Times we've seen this pattern
    correlation_strength FLOAT DEFAULT 0.5,     -- 0.0-1.0, increases with observations
    confidence FLOAT DEFAULT 0.3,               -- Confidence in this pattern

    -- Timing characteristics
    typical_delay_hours FLOAT,          -- How long between cause and effect
    time_window TEXT,                   -- When this pattern typically occurs

    -- Dosha context
    related_dosha TEXT,                 -- 'vata', 'pitta', 'kapha' if applicable
    ayurvedic_explanation TEXT,         -- Why this happens in Ayurvedic terms

    -- Example journal snippets that evidenced this pattern
    evidence_snippets JSONB DEFAULT '[]'::jsonb,
    /* Structure:
    [
        {"date": "2026-01-15", "snippet": "ate late, felt anxious next morning"},
        {"date": "2026-01-20", "snippet": "again had dinner at 10pm, woke up scattered"}
    ]
    */

    -- Metadata
    first_observed_at TIMESTAMPTZ DEFAULT now(),
    last_observed_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Unique constraint: one pattern per person per cause-effect pair
    UNIQUE(person_id, cause_type, cause_value, effect_type, effect_value)
);

-- =============================================================================
-- 2. Symptom Log Table
-- =============================================================================
-- Tracks symptoms/states to correlate with behaviors

CREATE TABLE IF NOT EXISTS symptom_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- What they're experiencing
    symptom_type TEXT NOT NULL,         -- 'physical', 'mental', 'emotional', 'energy'
    symptom_name TEXT NOT NULL,         -- 'anxiety', 'fatigue', 'scattered', 'irritable'
    severity FLOAT DEFAULT 0.5,         -- 0.0-1.0

    -- Context
    time_of_day TEXT,                   -- 'morning', 'afternoon', 'evening', 'night'
    related_entry_id UUID,              -- Reference to journal entry if applicable

    -- Ayurvedic mapping
    likely_dosha TEXT,                  -- Mapped dosha imbalance

    -- Source
    source TEXT DEFAULT 'inferred',     -- 'explicit' (user stated) or 'inferred' (from journal)
    source_text TEXT,                   -- Original text that indicated this

    -- Metadata
    occurred_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- 3. Behavior Log Table
-- =============================================================================
-- Tracks behaviors to correlate with symptoms

CREATE TABLE IF NOT EXISTS behavior_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,

    -- The behavior
    behavior_type TEXT NOT NULL,        -- 'food', 'sleep', 'exercise', 'work', 'social', 'substance'
    behavior_name TEXT NOT NULL,        -- 'late_dinner', 'skipped_sleep', 'coffee_evening'

    -- Quantification
    intensity FLOAT DEFAULT 0.5,        -- 0.0-1.0
    duration_minutes INTEGER,           -- How long

    -- Timing
    occurred_at TIMESTAMPTZ NOT NULL,
    time_of_day TEXT,                   -- 'morning', 'afternoon', 'evening', 'night'

    -- Ayurvedic mapping
    dosha_effect TEXT,                  -- Which dosha this likely affects
    effect_direction TEXT,              -- 'aggravates' or 'pacifies'

    -- Source
    source TEXT DEFAULT 'inferred',     -- 'explicit' or 'inferred'
    related_entry_id UUID,
    source_text TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- 4. Helper Functions
-- =============================================================================

-- Record or update a personal pattern
CREATE OR REPLACE FUNCTION upsert_personal_pattern(
    p_person_id UUID,
    p_cause_type TEXT,
    p_cause_value TEXT,
    p_effect_type TEXT,
    p_effect_value TEXT,
    p_related_dosha TEXT DEFAULT NULL,
    p_ayurvedic_explanation TEXT DEFAULT NULL,
    p_evidence_snippet TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_pattern_id UUID;
    v_new_count INTEGER;
    v_new_strength FLOAT;
    v_new_confidence FLOAT;
BEGIN
    -- Try to find existing pattern
    SELECT id, observation_count INTO v_pattern_id, v_new_count
    FROM personal_patterns
    WHERE person_id = p_person_id
      AND cause_type = p_cause_type
      AND cause_value = p_cause_value
      AND effect_type = p_effect_type
      AND effect_value = p_effect_value;

    IF v_pattern_id IS NOT NULL THEN
        -- Update existing pattern
        v_new_count := v_new_count + 1;
        -- Correlation strength increases logarithmically with observations
        v_new_strength := LEAST(0.95, 0.5 + (0.15 * LN(v_new_count + 1)));
        -- Confidence increases more slowly
        v_new_confidence := LEAST(0.9, 0.3 + (0.1 * LN(v_new_count + 1)));

        UPDATE personal_patterns
        SET observation_count = v_new_count,
            correlation_strength = v_new_strength,
            confidence = v_new_confidence,
            last_observed_at = now(),
            updated_at = now(),
            evidence_snippets = CASE
                WHEN p_evidence_snippet IS NOT NULL
                THEN evidence_snippets || jsonb_build_object(
                    'date', CURRENT_DATE::TEXT,
                    'snippet', p_evidence_snippet
                )
                ELSE evidence_snippets
            END,
            ayurvedic_explanation = COALESCE(p_ayurvedic_explanation, ayurvedic_explanation)
        WHERE id = v_pattern_id;

        RETURN v_pattern_id;
    ELSE
        -- Create new pattern
        INSERT INTO personal_patterns (
            person_id, cause_type, cause_value, effect_type, effect_value,
            related_dosha, ayurvedic_explanation,
            evidence_snippets
        ) VALUES (
            p_person_id, p_cause_type, p_cause_value, p_effect_type, p_effect_value,
            p_related_dosha, p_ayurvedic_explanation,
            CASE
                WHEN p_evidence_snippet IS NOT NULL
                THEN jsonb_build_array(jsonb_build_object('date', CURRENT_DATE::TEXT, 'snippet', p_evidence_snippet))
                ELSE '[]'::jsonb
            END
        )
        RETURNING id INTO v_pattern_id;

        RETURN v_pattern_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Query patterns that explain a symptom
CREATE OR REPLACE FUNCTION query_patterns_for_effect(
    p_person_id UUID,
    p_effect_type TEXT,
    p_effect_value TEXT,
    p_min_confidence FLOAT DEFAULT 0.4
) RETURNS TABLE (
    cause_type TEXT,
    cause_value TEXT,
    correlation_strength FLOAT,
    confidence FLOAT,
    observation_count INTEGER,
    ayurvedic_explanation TEXT,
    related_dosha TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pp.cause_type,
        pp.cause_value,
        pp.correlation_strength,
        pp.confidence,
        pp.observation_count,
        pp.ayurvedic_explanation,
        pp.related_dosha
    FROM personal_patterns pp
    WHERE pp.person_id = p_person_id
      AND pp.effect_type = p_effect_type
      AND pp.effect_value = p_effect_value
      AND pp.confidence >= p_min_confidence
    ORDER BY pp.correlation_strength DESC, pp.observation_count DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Get recent behaviors for correlation
CREATE OR REPLACE FUNCTION get_recent_behaviors(
    p_person_id UUID,
    p_hours_back INTEGER DEFAULT 48
) RETURNS TABLE (
    behavior_type TEXT,
    behavior_name TEXT,
    occurred_at TIMESTAMPTZ,
    dosha_effect TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        bl.behavior_type,
        bl.behavior_name,
        bl.occurred_at,
        bl.dosha_effect
    FROM behavior_log bl
    WHERE bl.person_id = p_person_id
      AND bl.occurred_at > now() - (p_hours_back || ' hours')::INTERVAL
    ORDER BY bl.occurred_at DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 5. Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_personal_patterns_person ON personal_patterns(person_id);
CREATE INDEX IF NOT EXISTS idx_personal_patterns_effect ON personal_patterns(effect_type, effect_value);
CREATE INDEX IF NOT EXISTS idx_personal_patterns_strength ON personal_patterns(correlation_strength DESC);

CREATE INDEX IF NOT EXISTS idx_symptom_log_person ON symptom_log(person_id);
CREATE INDEX IF NOT EXISTS idx_symptom_log_occurred ON symptom_log(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_symptom_log_symptom ON symptom_log(symptom_type, symptom_name);

CREATE INDEX IF NOT EXISTS idx_behavior_log_person ON behavior_log(person_id);
CREATE INDEX IF NOT EXISTS idx_behavior_log_occurred ON behavior_log(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavior_log_behavior ON behavior_log(behavior_type, behavior_name);

-- =============================================================================
-- 6. Triggers
-- =============================================================================

CREATE OR REPLACE FUNCTION update_personal_patterns_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_personal_patterns_updated
BEFORE UPDATE ON personal_patterns
FOR EACH ROW EXECUTE FUNCTION update_personal_patterns_timestamp();

-- =============================================================================
-- 7. Comments
-- =============================================================================

COMMENT ON TABLE personal_patterns IS 'User-specific cause-effect patterns learned from journal entries and observations';
COMMENT ON TABLE symptom_log IS 'Log of symptoms/states for correlation analysis';
COMMENT ON TABLE behavior_log IS 'Log of behaviors for correlation with symptoms';
COMMENT ON FUNCTION upsert_personal_pattern IS 'Record or strengthen a cause-effect pattern observation';
COMMENT ON FUNCTION query_patterns_for_effect IS 'Find patterns that could explain a symptom/effect';

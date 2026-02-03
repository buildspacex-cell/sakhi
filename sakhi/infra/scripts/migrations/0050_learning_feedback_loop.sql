-- Learning & Feedback Loop Tables
-- A.7 Learning Pipeline + A.8 Preference Feedback Loop

-- ============================================================================
-- A.8.1 Choice Logger - Track user selections between options
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_choices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),

    -- What was offered
    choice_context TEXT NOT NULL,     -- 'restaurant', 'product', 'activity', 'food'
    options_presented JSONB NOT NULL, -- Array of options shown
    option_count INT DEFAULT 2,

    -- What was chosen
    chosen_option JSONB,              -- The selected option details
    chosen_index INT,                 -- Which position (0-indexed)

    -- Why they might have chosen
    inferred_reasons JSONB DEFAULT '[]',  -- LLM-inferred reasons

    -- Context
    conversation_id TEXT,
    recommendation_id TEXT,           -- Links to recommendation_feedback

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_choices_person ON user_choices(person_id);
CREATE INDEX IF NOT EXISTS idx_user_choices_context ON user_choices(person_id, choice_context);
CREATE INDEX IF NOT EXISTS idx_user_choices_recent ON user_choices(person_id, created_at DESC);

-- ============================================================================
-- A.8.2 Recommendation Feedback - Track feedback on recommendations
-- ============================================================================
CREATE TABLE IF NOT EXISTS recommendation_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),

    -- What was recommended
    recommendation_type TEXT NOT NULL, -- 'product', 'food', 'activity', 'wellness'
    recommendation_domain TEXT,        -- 'fragrance', 'food', 'travel', etc.
    recommendation_content JSONB NOT NULL, -- Full recommendation details

    -- Explicit feedback
    feedback_type TEXT,               -- 'thumbs_up', 'thumbs_down', 'dismiss', 'follow', 'complaint'
    feedback_text TEXT,               -- Optional text feedback ("too spicy", "loved it")
    rating FLOAT,                     -- 1-5 or -1 to 1

    -- Implicit signals
    was_followed BOOLEAN,             -- Did user act on it?
    was_reordered BOOLEAN,            -- Did they order again?
    time_to_action_seconds INT,       -- How long before acting

    -- Preference dimensions affected
    affected_dimensions JSONB DEFAULT '[]', -- [{domain, dimension, direction}]

    -- Context
    conversation_id TEXT,
    choice_id UUID REFERENCES user_choices(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    acted_at TIMESTAMPTZ              -- When they followed the recommendation
);

CREATE INDEX IF NOT EXISTS idx_rec_feedback_person ON recommendation_feedback(person_id);
CREATE INDEX IF NOT EXISTS idx_rec_feedback_type ON recommendation_feedback(person_id, recommendation_type);
CREATE INDEX IF NOT EXISTS idx_rec_feedback_domain ON recommendation_feedback(person_id, recommendation_domain);
CREATE INDEX IF NOT EXISTS idx_rec_feedback_recent ON recommendation_feedback(person_id, created_at DESC);

-- ============================================================================
-- A.8.3 Preference Adjustments - Track how preferences change
-- ============================================================================
CREATE TABLE IF NOT EXISTS preference_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- What changed
    domain TEXT NOT NULL,
    dimension TEXT NOT NULL,
    old_value FLOAT,
    new_value FLOAT,
    adjustment FLOAT,                 -- The delta

    -- Why it changed
    trigger_type TEXT NOT NULL,       -- 'feedback', 'choice', 'explicit', 'decay'
    trigger_id UUID,                  -- Links to feedback or choice
    evidence_text TEXT,

    -- Confidence tracking
    old_confidence FLOAT,
    new_confidence FLOAT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pref_adj_person ON preference_adjustments(person_id);
CREATE INDEX IF NOT EXISTS idx_pref_adj_domain ON preference_adjustments(person_id, domain);
CREATE INDEX IF NOT EXISTS idx_pref_adj_trigger ON preference_adjustments(trigger_type, trigger_id);

-- ============================================================================
-- A.7.5 Learning Triggers - Track when learning runs occurred
-- ============================================================================
CREATE TABLE IF NOT EXISTS learning_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),

    -- Run details
    run_type TEXT NOT NULL,           -- 'correlation', 'preference_update', 'full'
    trigger_reason TEXT,              -- 'scheduled', 'threshold', 'manual'

    -- Results
    behaviors_processed INT DEFAULT 0,
    symptoms_processed INT DEFAULT 0,
    patterns_detected INT DEFAULT 0,
    patterns_strengthened INT DEFAULT 0,
    preferences_updated INT DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INT,

    -- Status
    status TEXT DEFAULT 'running',    -- 'running', 'completed', 'failed'
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_learning_runs_person ON learning_runs(person_id);
CREATE INDEX IF NOT EXISTS idx_learning_runs_recent ON learning_runs(person_id, started_at DESC);

-- ============================================================================
-- Add missing columns to behavior_log if needed
-- ============================================================================
DO $$
BEGIN
    -- Add time_of_day column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'behavior_log' AND column_name = 'time_of_day') THEN
        ALTER TABLE behavior_log ADD COLUMN time_of_day TEXT;
    END IF;

    -- Add source column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'behavior_log' AND column_name = 'source') THEN
        ALTER TABLE behavior_log ADD COLUMN source TEXT DEFAULT 'inferred';
    END IF;

    -- Add related_entry_id column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'behavior_log' AND column_name = 'related_entry_id') THEN
        ALTER TABLE behavior_log ADD COLUMN related_entry_id TEXT;
    END IF;

    -- Add source_text column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'behavior_log' AND column_name = 'source_text') THEN
        ALTER TABLE behavior_log ADD COLUMN source_text TEXT;
    END IF;
END $$;

-- ============================================================================
-- Add missing columns to symptom_log if needed
-- ============================================================================
DO $$
BEGIN
    -- Add symptom_name column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'symptom_log' AND column_name = 'symptom_name') THEN
        ALTER TABLE symptom_log ADD COLUMN symptom_name TEXT;
    END IF;

    -- Add time_of_day column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'symptom_log' AND column_name = 'time_of_day') THEN
        ALTER TABLE symptom_log ADD COLUMN time_of_day TEXT;
    END IF;

    -- Add likely_dosha column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'symptom_log' AND column_name = 'likely_dosha') THEN
        ALTER TABLE symptom_log ADD COLUMN likely_dosha TEXT;
    END IF;

    -- Add source column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'symptom_log' AND column_name = 'source') THEN
        ALTER TABLE symptom_log ADD COLUMN source TEXT DEFAULT 'inferred';
    END IF;

    -- Add related_entry_id column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'symptom_log' AND column_name = 'related_entry_id') THEN
        ALTER TABLE symptom_log ADD COLUMN related_entry_id TEXT;
    END IF;

    -- Add source_text column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'symptom_log' AND column_name = 'source_text') THEN
        ALTER TABLE symptom_log ADD COLUMN source_text TEXT;
    END IF;
END $$;

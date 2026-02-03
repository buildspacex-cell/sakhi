-- Migration 0047: Demo Tables for Causal Reasoning
-- Date: 2026-02-01
--
-- Creates tables needed for the reflective intelligence demo:
-- 1. personal_patterns - Learned cause-effect patterns for a user
-- 2. behavior_log - Recent behaviors for correlation
-- 3. symptom_episodes - Past symptom episodes and what helped

-- =============================================================================
-- PERSONAL PATTERNS TABLE
-- =============================================================================
-- Stores learned correlations: "When you do X, you tend to feel Y"
-- Used by causal_reasoning.py for "Why am I feeling X?" answers

CREATE TABLE IF NOT EXISTS personal_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- Cause side
    cause_type TEXT NOT NULL,  -- 'behavior', 'food', 'sleep', 'weather', etc.
    cause_value TEXT NOT NULL, -- e.g., 'late_dinner', 'skipped_exercise'

    -- Effect side
    effect_type TEXT NOT NULL, -- 'symptom', 'mood', 'energy', etc.
    effect_value TEXT NOT NULL, -- e.g., 'scattered', 'anxious', 'low_energy'

    -- Correlation metrics
    correlation_strength FLOAT NOT NULL DEFAULT 0.5 CHECK (correlation_strength >= 0 AND correlation_strength <= 1),
    confidence FLOAT NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    observation_count INT NOT NULL DEFAULT 1,

    -- Ayurvedic context
    ayurvedic_explanation TEXT,
    related_dosha TEXT CHECK (related_dosha IN ('vata', 'pitta', 'kapha') OR related_dosha IS NULL),

    -- Tracking
    first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicates
    UNIQUE (person_id, cause_type, cause_value, effect_type, effect_value)
);

CREATE INDEX IF NOT EXISTS idx_personal_patterns_person ON personal_patterns(person_id);
CREATE INDEX IF NOT EXISTS idx_personal_patterns_effect ON personal_patterns(person_id, effect_type, effect_value);
CREATE INDEX IF NOT EXISTS idx_personal_patterns_cause ON personal_patterns(person_id, cause_type, cause_value);
CREATE INDEX IF NOT EXISTS idx_personal_patterns_dosha ON personal_patterns(person_id, related_dosha) WHERE related_dosha IS NOT NULL;

COMMENT ON TABLE personal_patterns IS 'Learned cause-effect patterns for each user - "When you do X, you feel Y"';

-- =============================================================================
-- BEHAVIOR LOG TABLE
-- =============================================================================
-- Recent behaviors (last 48-72 hours) for correlation analysis
-- Used by causal_reasoning.py to find likely triggers

CREATE TABLE IF NOT EXISTS behavior_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- Behavior info
    behavior_type TEXT NOT NULL,  -- 'food', 'exercise', 'sleep', 'work', etc.
    behavior_name TEXT NOT NULL,  -- e.g., 'late_dinner', 'morning_walk'
    occurred_at TIMESTAMPTZ NOT NULL,

    -- Ayurvedic effects
    dosha_effect TEXT CHECK (dosha_effect IN ('vata', 'pitta', 'kapha') OR dosha_effect IS NULL),
    effect_direction TEXT CHECK (effect_direction IN ('aggravates', 'balances', 'neutral') OR effect_direction IS NULL),
    intensity TEXT CHECK (intensity IN ('mild', 'moderate', 'strong') OR intensity IS NULL),

    -- Context
    source_text TEXT,  -- Original text that mentioned this behavior
    source_type TEXT DEFAULT 'conversation', -- 'conversation', 'journal', 'observation'

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_behavior_log_person ON behavior_log(person_id);
CREATE INDEX IF NOT EXISTS idx_behavior_log_recent ON behavior_log(person_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavior_log_type ON behavior_log(person_id, behavior_type, occurred_at DESC);

COMMENT ON TABLE behavior_log IS 'Recent behaviors for causal correlation - what happened in last 48 hours';

-- =============================================================================
-- SYMPTOM EPISODES TABLE
-- =============================================================================
-- Historical episodes of symptoms and what helped
-- Used for "Last time I felt X, this is what helped" queries

CREATE TABLE IF NOT EXISTS symptom_episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- Episode info
    symptom TEXT NOT NULL,  -- 'scattered', 'anxious', 'sluggish', etc.
    occurred_at TIMESTAMPTZ NOT NULL,
    duration_hours INT,  -- How long it lasted

    -- Cause analysis
    likely_cause TEXT,  -- What we think caused it

    -- Recovery
    what_helped JSONB DEFAULT '[]',  -- List of interventions that helped
    recovery_time_hours INT,  -- How long until recovery

    -- Notes
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_symptom_episodes_person ON symptom_episodes(person_id);
CREATE INDEX IF NOT EXISTS idx_symptom_episodes_symptom ON symptom_episodes(person_id, symptom, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_symptom_episodes_recent ON symptom_episodes(person_id, occurred_at DESC);

COMMENT ON TABLE symptom_episodes IS 'Past symptom episodes and what helped - for "last time" lookups';

-- =============================================================================
-- DONE
-- =============================================================================

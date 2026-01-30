-- Pattern occurrences: Track pattern detections before crystallization
-- Part of Pattern Crystallization Layer - patterns must meet thresholds before promotion

-- Pattern occurrences (raw detections, logged per-turn)
CREATE TABLE IF NOT EXISTS pattern_occurrences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN (
        'core_value', 'shadow', 'light', 'theme', 'concern',
        'relationship', 'goal', 'trait', 'contradiction'
    )),
    pattern_value TEXT NOT NULL,
    episode_id UUID,
    entry_id UUID,
    snippet TEXT,  -- Evidence snippet from the entry
    confidence FLOAT DEFAULT 0.5,
    sentiment FLOAT,  -- -1 to 1 if applicable
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pattern_occurrences_person ON pattern_occurrences(person_id);
CREATE INDEX IF NOT EXISTS idx_pattern_occurrences_person_type ON pattern_occurrences(person_id, pattern_type);
CREATE INDEX IF NOT EXISTS idx_pattern_occurrences_person_value ON pattern_occurrences(person_id, pattern_type, pattern_value);
CREATE INDEX IF NOT EXISTS idx_pattern_occurrences_detected ON pattern_occurrences(detected_at);

-- Crystallized patterns (promoted when thresholds met)
CREATE TABLE IF NOT EXISTS crystallized_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,

    -- Pattern identification
    pattern_type TEXT NOT NULL CHECK (pattern_type IN (
        'core_value', 'shadow', 'light', 'theme', 'concern',
        'relationship', 'goal', 'trait', 'contradiction'
    )),
    pattern_value TEXT NOT NULL,
    sub_topic TEXT,  -- Optional refinement

    -- The crystallized understanding
    summary TEXT,  -- Human-readable pattern description
    constitution_relevance TEXT,  -- How this relates to their dosha

    -- Evidence (provenance)
    evidence_ids UUID[] DEFAULT '{}',  -- Array of pattern_occurrence IDs
    evidence_snippets JSONB DEFAULT '[]',  -- [{occurrence_id, date, snippet}, ...]
    mention_count INTEGER NOT NULL DEFAULT 0,
    distinct_days INTEGER NOT NULL DEFAULT 0,

    -- Confidence and thresholds
    confidence FLOAT NOT NULL DEFAULT 0.0,
    threshold_met_at TIMESTAMPTZ,

    -- Trajectory tracking
    trajectory TEXT DEFAULT 'stable' CHECK (trajectory IN (
        'improving', 'worsening', 'stable', 'emerging', 'fading'
    )),
    trajectory_data JSONB DEFAULT '{}',

    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'emerging' CHECK (status IN (
        'emerging', 'active', 'fading', 'archived'
    )),
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    crystallized_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint per person + type + value
    CONSTRAINT unique_person_pattern UNIQUE (person_id, pattern_type, pattern_value)
);

CREATE INDEX IF NOT EXISTS idx_crystallized_person ON crystallized_patterns(person_id);
CREATE INDEX IF NOT EXISTS idx_crystallized_person_status ON crystallized_patterns(person_id, status);
CREATE INDEX IF NOT EXISTS idx_crystallized_person_type ON crystallized_patterns(person_id, pattern_type);

-- Crystallization log (audit trail)
CREATE TABLE IF NOT EXISTS crystallization_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    crystallized_pattern_id UUID REFERENCES crystallized_patterns(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL,
    pattern_value TEXT NOT NULL,
    occurrence_count INTEGER,
    distinct_days INTEGER,
    confidence FLOAT,
    span_days INTEGER,
    threshold_config JSONB,  -- The threshold config used
    evidence_ids UUID[],
    action TEXT CHECK (action IN ('crystallized', 'updated', 'trajectory_changed', 'archived')),
    crystallized_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crystallization_log_person ON crystallization_log(person_id);
CREATE INDEX IF NOT EXISTS idx_crystallization_log_pattern ON crystallization_log(crystallized_pattern_id);

-- Migration: 0040_body_state
-- Description: Add body_state to personal_model and create health data sync table
-- Purpose: Track physical/somatic state grounded in Ayurveda for complete personal intelligence

-- ============================================================================
-- 1. Add body_state column to personal_model
-- ============================================================================

ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS body_state JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN personal_model.body_state IS 'Physical/somatic state: vitals, sleep, energy, dosha body signs, agni, ojas, tension, prana';

-- ============================================================================
-- 2. Create health_data_sync table for raw health app data
-- ============================================================================

CREATE TABLE IF NOT EXISTS health_data_sync (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    source TEXT NOT NULL,  -- 'apple_health', 'android_health', 'self_report', 'wearable'
    data_type TEXT NOT NULL,  -- 'sleep', 'activity', 'heart', 'respiratory', 'nutrition', 'body', 'mindfulness'
    data JSONB NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,  -- When the measurement was taken
    synced_at TIMESTAMPTZ DEFAULT NOW(),  -- When we received it
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,

    CONSTRAINT fk_health_sync_person FOREIGN KEY (person_id)
        REFERENCES persons(id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_health_sync_person_type
    ON health_data_sync(person_id, data_type, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_health_sync_unprocessed
    ON health_data_sync(person_id, processed, synced_at DESC)
    WHERE NOT processed;

CREATE INDEX IF NOT EXISTS idx_health_sync_source
    ON health_data_sync(person_id, source, recorded_at DESC);

COMMENT ON TABLE health_data_sync IS 'Raw health data from Apple Health, Android Health Connect, wearables, and self-reports';

-- ============================================================================
-- 3. Create body_state_history for longitudinal tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS body_state_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    body_state JSONB NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Computed summary fields for easy querying
    overall_score FLOAT,
    vata_score FLOAT,
    pitta_score FLOAT,
    kapha_score FLOAT,
    ojas_level FLOAT,
    sleep_quality FLOAT,
    energy_level FLOAT,

    CONSTRAINT fk_body_history_person FOREIGN KEY (person_id)
        REFERENCES persons(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_body_history_person_time
    ON body_state_history(person_id, computed_at DESC);

-- Partition-ready index for time-series queries
CREATE INDEX IF NOT EXISTS idx_body_history_time
    ON body_state_history(computed_at DESC);

COMMENT ON TABLE body_state_history IS 'Historical body state snapshots for longitudinal health pattern analysis';

-- ============================================================================
-- 4. Create self_report_body table for user check-ins
-- ============================================================================

CREATE TABLE IF NOT EXISTS self_report_body (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- Energy & Vitality
    energy_level FLOAT,  -- 0-1
    fatigue_level FLOAT,  -- 0-1

    -- Body Sensations
    tension_neck_shoulders FLOAT,  -- 0-1
    tension_back FLOAT,
    tension_jaw FLOAT,
    tension_other TEXT,

    -- Digestion (Agni)
    hunger_level FLOAT,  -- 0-1
    digestion_quality TEXT,  -- 'good', 'sluggish', 'hyperactive', 'irregular'
    bloating BOOLEAN,
    elimination_regular BOOLEAN,

    -- Temperature
    feeling_cold BOOLEAN,
    feeling_hot BOOLEAN,

    -- Hydration
    hydration_level FLOAT,  -- 0-1

    -- Breath
    breath_quality TEXT,  -- 'deep', 'moderate', 'shallow', 'irregular'

    -- Cravings (reveal imbalances)
    cravings TEXT[],  -- ['sweet', 'salty', 'warm', 'cold', 'heavy', 'light']

    -- General
    notes TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_self_report_person FOREIGN KEY (person_id)
        REFERENCES persons(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_self_report_body_person
    ON self_report_body(person_id, recorded_at DESC);

COMMENT ON TABLE self_report_body IS 'User self-reported body sensations and Ayurvedic indicators';

-- ============================================================================
-- 5. Initialize body_state for existing users
-- ============================================================================

UPDATE personal_model
SET body_state = jsonb_build_object(
    'vitals', '{}'::jsonb,
    'sleep', '{}'::jsonb,
    'energy', jsonb_build_object('level', 0.5, 'trend', 'stable'),
    'activity', '{}'::jsonb,
    'dosha_body', jsonb_build_object(
        'vata_signs', jsonb_build_object('score', 0.0, 'signals', '[]'::jsonb),
        'pitta_signs', jsonb_build_object('score', 0.0, 'signals', '[]'::jsonb),
        'kapha_signs', jsonb_build_object('score', 0.0, 'signals', '[]'::jsonb),
        'dominant_imbalance', null
    ),
    'agni', jsonb_build_object('strength', 'moderate'),
    'ojas', jsonb_build_object('level', 0.5),
    'tension_map', '{}'::jsonb,
    'prana', jsonb_build_object('breath_quality', 'moderate', 'capacity_score', 0.5),
    'hydration', jsonb_build_object('level', 0.5),
    'summary', jsonb_build_object(
        'overall_score', 0.5,
        'primary_need', 'balance',
        'confidence', 0.0
    ),
    'updated_at', NOW(),
    'data_sources', '["initialization"]'::jsonb
)
WHERE body_state IS NULL OR body_state = '{}'::jsonb;

-- ============================================================================
-- Done
-- ============================================================================

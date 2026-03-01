-- Make pattern learning idempotent and efficient.
-- 1. Track each concrete behavior->symptom correlation once
-- 2. Deduplicate old personal_patterns rows
-- 3. Add indexes for the hot correlation path

CREATE TABLE IF NOT EXISTS behavior_symptom_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    behavior_log_id uuid NOT NULL,
    symptom_log_id uuid NOT NULL,
    cause_type text NOT NULL,
    cause_value text NOT NULL,
    effect_type text NOT NULL,
    effect_value text NOT NULL,
    related_dosha text,
    observed_at timestamp with time zone NOT NULL DEFAULT now(),
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

WITH ranked AS (
    SELECT
        id,
        person_id,
        cause_type,
        cause_value,
        effect_type,
        effect_value,
        observation_count,
        correlation_strength,
        confidence,
        first_observed_at,
        last_observed_at,
        ROW_NUMBER() OVER (
            PARTITION BY person_id, cause_type, cause_value, effect_type, effect_value
            ORDER BY last_observed_at DESC, created_at DESC, id DESC
        ) AS rn,
        SUM(observation_count) OVER (
            PARTITION BY person_id, cause_type, cause_value, effect_type, effect_value
        ) AS total_observation_count,
        MAX(correlation_strength) OVER (
            PARTITION BY person_id, cause_type, cause_value, effect_type, effect_value
        ) AS max_correlation_strength,
        MAX(confidence) OVER (
            PARTITION BY person_id, cause_type, cause_value, effect_type, effect_value
        ) AS max_confidence,
        MIN(first_observed_at) OVER (
            PARTITION BY person_id, cause_type, cause_value, effect_type, effect_value
        ) AS min_first_observed_at,
        MAX(last_observed_at) OVER (
            PARTITION BY person_id, cause_type, cause_value, effect_type, effect_value
        ) AS max_last_observed_at
    FROM personal_patterns
)
UPDATE personal_patterns p
SET observation_count = ranked.total_observation_count,
    correlation_strength = ranked.max_correlation_strength,
    confidence = ranked.max_confidence,
    first_observed_at = ranked.min_first_observed_at,
    last_observed_at = ranked.max_last_observed_at,
    updated_at = now()
FROM ranked
WHERE p.id = ranked.id
  AND ranked.rn = 1;

WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY person_id, cause_type, cause_value, effect_type, effect_value
            ORDER BY last_observed_at DESC, created_at DESC, id DESC
        ) AS rn
    FROM personal_patterns
)
DELETE FROM personal_patterns p
USING ranked
WHERE p.id = ranked.id
  AND ranked.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_behavior_symptom_log_unique
    ON behavior_symptom_log (person_id, behavior_log_id, symptom_log_id);

CREATE INDEX IF NOT EXISTS idx_behavior_symptom_log_person_observed
    ON behavior_symptom_log (person_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_behavior_log_pattern_lookup
    ON behavior_log (person_id, effect_direction, dosha_effect, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_symptom_log_pattern_lookup
    ON symptom_log (person_id, likely_dosha, occurred_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_personal_patterns_unique
    ON personal_patterns (person_id, cause_type, cause_value, effect_type, effect_value);

CREATE INDEX IF NOT EXISTS idx_personal_patterns_effect_lookup
    ON personal_patterns (person_id, effect_type, effect_value, confidence DESC);

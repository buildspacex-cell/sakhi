-- Migration: 0028_friction_framework
-- Purpose: Add Friction Framework columns to personal_model for MVP
-- Date: 2026-01-22

-- =============================================================================
-- OPERATING SYSTEM (Prakruti / Constitutional Type)
-- =============================================================================
-- Structure:
-- {
--   "type": "Adaptive-Performance",
--   "primary": "Adaptive",
--   "secondary": "Performance",
--   "dosha_baseline": {"vata": 0.45, "pitta": 0.35, "kapha": 0.20},
--   "onboarding_responses": {...},
--   "computed_at": "2026-01-22T10:00:00Z",
--   "source": "full_onboarding",
--   "is_soft_constraint": true,
--   "override_by_observation": true
-- }

ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS operating_system JSONB DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_personal_model_operating_system_type
ON personal_model ((operating_system->>'type'));

COMMENT ON COLUMN personal_model.operating_system IS
'User constitutional type (Prakruti) as Operating System. Contains dosha baseline and onboarding data. Soft constraint that can be overridden by observed behavior.';


-- =============================================================================
-- LIFE CONTEXT
-- =============================================================================
-- Structure:
-- {
--   "age_range": "35-44",
--   "location": "San Francisco, USA",
--   "active_roles": ["professional", "partner_family"],
--   "life_phase": "building",
--   "responsibility_load": "shared",
--   "allergies": "dairy",
--   "foods_avoided": "gluten"
-- }

ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS life_context JSONB DEFAULT NULL;

COMMENT ON COLUMN personal_model.life_context IS
'User life context including age, location, roles, life phase, and dietary constraints. Used for personalized recommendations.';


-- =============================================================================
-- DECISION PROFILE
-- =============================================================================
-- Structure:
-- {
--   "primary_driver": "make_progress",
--   "risk_tendency": "calculated_risk",
--   "time_horizon": "year_two",
--   "energy_tradeoff": "case_by_case",
--   "flexibility_style": "reorganize"
-- }

ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS decision_profile JSONB DEFAULT NULL;

COMMENT ON COLUMN personal_model.decision_profile IS
'User decision-making patterns. Used to understand tradeoff preferences and provide aligned guidance.';

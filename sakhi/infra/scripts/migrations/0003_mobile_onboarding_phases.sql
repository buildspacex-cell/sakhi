-- Migration: 0003_mobile_onboarding_phases
-- Description: Add phase tracking columns for mobile onboarding flow
-- Date: 2026-02-07
--
-- This migration supports the mobile app's phased onboarding flow:
-- - Phase 1: 3 mandatory questions (clarity_window, pacing_under_demand, first_stress_signal)
-- - Phase 2a: 3 optional questions (current_energy, body_request, fastest_recovery)
-- - Phase 2b: 7 optional questions (life context and decision-making)
--
-- Mobile users can exit to voice conversation after any phase.

-- =============================================================================
-- AUTH_USERS TABLE CHANGES
-- =============================================================================

-- Add phase tracking columns to auth_users
ALTER TABLE auth_users
ADD COLUMN IF NOT EXISTS onboarding_phase TEXT DEFAULT NULL;

ALTER TABLE auth_users
ADD COLUMN IF NOT EXISTS phase1_completed_at TIMESTAMPTZ DEFAULT NULL;

ALTER TABLE auth_users
ADD COLUMN IF NOT EXISTS phase2a_completed_at TIMESTAMPTZ DEFAULT NULL;

ALTER TABLE auth_users
ADD COLUMN IF NOT EXISTS phase2b_completed_at TIMESTAMPTZ DEFAULT NULL;

-- Add comment explaining the columns
COMMENT ON COLUMN auth_users.onboarding_phase IS 'Current onboarding phase: phase1, phase2a, phase2b, or full (web)';
COMMENT ON COLUMN auth_users.phase1_completed_at IS 'When Phase 1 (3 mandatory questions) was completed';
COMMENT ON COLUMN auth_users.phase2a_completed_at IS 'When Phase 2a (energy/recovery questions) was completed';
COMMENT ON COLUMN auth_users.phase2b_completed_at IS 'When Phase 2b (life context questions) was completed';

-- =============================================================================
-- PERSONAL_MODEL TABLE CHANGES
-- =============================================================================

-- Add onboarding source and phase tracking to personal_model
ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS onboarding_source TEXT DEFAULT 'web';

ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS onboarding_phase TEXT DEFAULT 'full';

ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS phase1_completed_at TIMESTAMPTZ DEFAULT NULL;

ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS phase2a_completed_at TIMESTAMPTZ DEFAULT NULL;

ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS phase2b_completed_at TIMESTAMPTZ DEFAULT NULL;

-- Add comments explaining the columns
COMMENT ON COLUMN personal_model.onboarding_source IS 'Source of onboarding: web or mobile';
COMMENT ON COLUMN personal_model.onboarding_phase IS 'Last completed phase: phase1, phase2a, phase2b, or full';
COMMENT ON COLUMN personal_model.phase1_completed_at IS 'When Phase 1 was completed (mobile flow)';
COMMENT ON COLUMN personal_model.phase2a_completed_at IS 'When Phase 2a was completed (mobile flow)';
COMMENT ON COLUMN personal_model.phase2b_completed_at IS 'When Phase 2b was completed (mobile flow)';

-- =============================================================================
-- INDEXES FOR QUERYING
-- =============================================================================

-- Index for finding users by onboarding phase (useful for analytics and follow-up)
CREATE INDEX IF NOT EXISTS idx_auth_users_onboarding_phase
ON auth_users(onboarding_phase)
WHERE onboarding_phase IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_personal_model_onboarding_source
ON personal_model(onboarding_source);

CREATE INDEX IF NOT EXISTS idx_personal_model_onboarding_phase
ON personal_model(onboarding_phase);

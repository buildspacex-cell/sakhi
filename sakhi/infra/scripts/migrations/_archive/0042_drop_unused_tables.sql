-- Migration 0042: Drop unused empty tables
--
-- These tables have ZERO code references and ZERO rows.
-- Audit performed: 2026-01-28
--
-- Tables kept:
--   - All tables with code references (118 tables)
--   - All Supabase auth tables
--   - All cache tables (active workers)

-- ============================================================================
-- PLANNING SYSTEM - Created but never populated
-- ============================================================================
DROP TABLE IF EXISTS goal_suggestions CASCADE;
DROP TABLE IF EXISTS intent_extractions CASCADE;

-- ============================================================================
-- LEGACY MEMORY TABLES - No code references
-- ============================================================================
DROP TABLE IF EXISTS links CASCADE;
DROP TABLE IF EXISTS memory_identity_edges CASCADE;
DROP TABLE IF EXISTS memory_preferences CASCADE;
DROP TABLE IF EXISTS memory_semantic_traits CASCADE;

-- ============================================================================
-- LEGACY REFLECTION/META TABLES - No code references
-- ============================================================================
DROP TABLE IF EXISTS mental_impression CASCADE;
DROP TABLE IF EXISTS meta_audit CASCADE;
DROP TABLE IF EXISTS meta_reflection_scores_backup CASCADE;
DROP TABLE IF EXISTS reflection_actions CASCADE;
DROP TABLE IF EXISTS reflection_scores CASCADE;
DROP TABLE IF EXISTS reflection_test_cases CASCADE;

-- ============================================================================
-- LEGACY PLANNING TABLES - No code references
-- ============================================================================
DROP TABLE IF EXISTS milestones CASCADE;
DROP TABLE IF EXISTS objectives CASCADE;
DROP TABLE IF EXISTS observations CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS short_horizon CASCADE;

-- ============================================================================
-- LEGACY PERSON/PROFILE TABLES - No code references
-- ============================================================================
DROP TABLE IF EXISTS people_roles CASCADE;
DROP TABLE IF EXISTS person_aspects CASCADE;
DROP TABLE IF EXISTS prompt_profiles CASCADE;

-- ============================================================================
-- LEGACY RELATIONSHIP/THEME TABLES - No code references
-- ============================================================================
DROP TABLE IF EXISTS relationship_arcs CASCADE;
DROP TABLE IF EXISTS theme_links CASCADE;
DROP TABLE IF EXISTS value_alignment CASCADE;

-- ============================================================================
-- LEGACY SIGNAL/RHYTHM TABLES - No code references
-- ============================================================================
DROP TABLE IF EXISTS situational_signals CASCADE;
DROP TABLE IF EXISTS timeseries_signals CASCADE;
DROP TABLE IF EXISTS user_rhythm_profile CASCADE;

-- ============================================================================
-- DEBUG/AUDIT TABLES - Safe to drop
-- ============================================================================
DROP TABLE IF EXISTS observe_pipeline_audit CASCADE;
DROP TABLE IF EXISTS task_enrichment_log CASCADE;
DROP TABLE IF EXISTS turn_async_jobs CASCADE;

-- ============================================================================
-- BACKUP TABLES - Safe to drop
-- ============================================================================
DROP TABLE IF EXISTS personal_model_snapshots CASCADE;

-- ============================================================================
-- LEGACY PRESENCE/MEMORY TABLES - No code references
-- ============================================================================
DROP TABLE IF EXISTS presence_prompts CASCADE;
DROP TABLE IF EXISTS user_memories CASCADE;

-- ============================================================================
-- Total: 31 tables dropped
-- ============================================================================

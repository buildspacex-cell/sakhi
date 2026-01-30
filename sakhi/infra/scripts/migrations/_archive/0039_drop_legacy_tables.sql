-- Migration 0039: Drop truly unused legacy tables
--
-- This is a CONSERVATIVE cleanup based on codebase sweep (Jan 2026).
-- Only drops tables with ZERO remaining code references.
--
-- Sakhi core now uses: personal_model, memory_episodic, journal_entries,
-- pattern_occurrences, crystallized_patterns, intents, memory_nodes, memory_edges

-- ============================================================================
-- ANCHOR/ASPECT SYSTEM - No code references found
-- ============================================================================
DROP TABLE IF EXISTS anchor_feature_map CASCADE;
DROP TABLE IF EXISTS anchor_weights CASCADE;
DROP TABLE IF EXISTS aspect_features CASCADE;
DROP TABLE IF EXISTS aspect_kinds CASCADE;

-- ============================================================================
-- LEGACY REFLECTION/BRIDGING - No code references found
-- ============================================================================
DROP TABLE IF EXISTS bridging_reflections CASCADE;
DROP TABLE IF EXISTS calibration_profile CASCADE;

-- ============================================================================
-- LEGACY CONTEXT SUMMARIES - No code references found
-- ============================================================================
DROP TABLE IF EXISTS context_compact_summaries CASCADE;

-- ============================================================================
-- LEGACY EMOTIONAL/ENERGY STATE - No code references found
-- (Note: emotional_tones is still used by sync_analytics_cache, kept for now)
-- ============================================================================
DROP TABLE IF EXISTS emotional_signature CASCADE;
DROP TABLE IF EXISTS energetic_state CASCADE;
DROP TABLE IF EXISTS energy_cycles CASCADE;
DROP TABLE IF EXISTS energy_summary_monthly CASCADE;
DROP TABLE IF EXISTS energy_summary_weekly CASCADE;

-- ============================================================================
-- LEGACY LIFE TABLES - No code references found
-- ============================================================================
DROP TABLE IF EXISTS life_event_links CASCADE;
DROP TABLE IF EXISTS life_phases CASCADE;

-- ============================================================================
-- ELEMENTAL DEBUG TABLES - No code references found
-- (keeping elemental_signal_stm for ayurvedic_pipeline)
-- ============================================================================
DROP TABLE IF EXISTS elemental_episode_link CASCADE;
DROP TABLE IF EXISTS elemental_summary_monthly CASCADE;
DROP TABLE IF EXISTS elemental_summary_weekly CASCADE;

-- ============================================================================
-- LEGACY RHYTHM TABLES - No code references found
-- (from previous migration 0038, ensure dropped)
-- ============================================================================
DROP TABLE IF EXISTS rhythm_events CASCADE;
DROP TABLE IF EXISTS rhythm_daily_curve CASCADE;
DROP TABLE IF EXISTS rhythm_chronotype CASCADE;
DROP TABLE IF EXISTS rhythm_state CASCADE;

-- ============================================================================
-- TABLES KEPT (still have code references - need future cleanup)
-- ============================================================================
-- aw_* (aw_event, aw_edge, aw_episode, aw_redaction)
--   → Used by: routers/awareness.py, routers/memory.py, routers/clarity.py, routers/intel.py
--   → Status: Active HTTP endpoints, needs API deprecation before removal
--
-- body_metrics, breath_sessions
--   → Used by: routes/breath.py, sync_breath_to_body.py, update_system_tempo.py
--   → Status: Active endpoints + scheduled workers
--
-- conflict_records
--   → Used by: routers/soul.py
--   → Status: Active endpoint
--
-- context_recalls
--   → Used by: services/conversation_v2/conversation_context_builder.py
--   → Status: Active conversation system
--
-- dialog_states
--   → Used by: core/dialog_state.py (core module)
--   → Status: Active core module
--
-- emotional_tones
--   → Used by: tasks/sync_analytics_cache.py
--   → Status: Scheduled worker
--
-- environment_context
--   → Used by: routes/environment.py
--   → Status: Active endpoint
--
-- episodes
--   → Used by: routers/soul.py, services/narratives/episodic.py
--   → Status: Active endpoints
--
-- identity_evolution_events, identity_signatures, life_arcs
--   → Used by: routers/soul.py, logic/brain/brain_engine.py
--   → Status: Dormant but referenced; needs migration to personal_model
--
-- facts
--   → Code uses "known facts" concept, not a separate table
--
-- ============================================================================
-- CORE TABLES (essential for personal intelligence)
-- ============================================================================
-- personal_model - Central state (operating_system, soul_state, emotion_state, rhythm_state)
-- memory_episodic - Episodic memories from conversations
-- journal_entries - Raw conversation turns
-- conversation_turns, conversation_sessions, conversation_state - Conversation tracking
-- pattern_occurrences, crystallized_patterns - Pattern detection + confirmation
-- intents, goals, goal_suggestions, goal_history - Planning system
-- memory_nodes, memory_edges - Cross-entity knowledge graph
-- elemental_signal_stm - Ayurvedic pipeline short-term memory
-- ay_nodes, ay_edges - Ayurvedic knowledge graph
-- All cache tables (daily_reflection_cache, forecast_cache, etc.)
-- All auth tables (managed by Supabase)

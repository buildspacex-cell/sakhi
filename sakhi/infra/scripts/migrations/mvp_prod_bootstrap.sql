-- Curated MVP production bootstrap
-- Date: 2026-03-19
-- Purpose: create only the schema required for the current chat + continuity MVP
-- Notes:
--   - This is a fresh-database bootstrap, not a sequential migration.
--   - Run on a new database only.
--   - Import data after schema creation using docs/guides/prod-mvp-database-manifest.md.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- Core identity
-- =============================================================================

CREATE TABLE IF NOT EXISTS persons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID UNIQUE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_sign_in_at TIMESTAMPTZ,
    onboarding_completed_at TIMESTAMPTZ,
    onboarding_phase TEXT,
    phase1_completed_at TIMESTAMPTZ,
    phase2a_completed_at TIMESTAMPTZ,
    phase2b_completed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- =============================================================================
-- Journal evidence
-- =============================================================================

CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    raw_encrypted BYTEA,
    cleaned TEXT,
    facets JSONB NOT NULL DEFAULT '{}'::jsonb,
    salience REAL NOT NULL DEFAULT 0,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    content TEXT,
    title TEXT,
    fts TSVECTOR,
    raw TEXT,
    encrypted_preview TEXT,
    facets_v2 JSONB DEFAULT '{}'::jsonb,
    cleaned_tsv TSVECTOR,
    narrative JSONB NOT NULL DEFAULT '{}'::jsonb,
    debug_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    layer TEXT,
    tags TEXT[] DEFAULT '{}'::text[],
    source_ref JSONB DEFAULT '{}'::jsonb,
    mood TEXT,
    person_id UUID REFERENCES persons(id) ON DELETE SET NULL,
    processing_state TEXT NOT NULL DEFAULT 'queued',
    processing_attempts INTEGER NOT NULL DEFAULT 0,
    processed_at TIMESTAMPTZ,
    processing_error JSONB,
    ack_text TEXT,
    worker_enrichment JSONB,
    input_type TEXT,
    client_context JSONB DEFAULT '{}'::jsonb,
    language TEXT,
    timezone TEXT,
    user_tags TEXT[] DEFAULT '{}'::text[]
);

CREATE INDEX IF NOT EXISTS idx_journal_entries_user_ts
    ON journal_entries (user_id, ts DESC, created_at DESC, id);

CREATE INDEX IF NOT EXISTS idx_journal_entries_person_ts
    ON journal_entries (person_id, ts DESC, created_at DESC, id);

CREATE INDEX IF NOT EXISTS idx_journal_entries_processing_state
    ON journal_entries (processing_state, created_at DESC);

CREATE TABLE IF NOT EXISTS journal_embeddings (
    entry_id UUID PRIMARY KEY REFERENCES journal_entries(id) ON DELETE CASCADE,
    model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now(),
    embedding_vec VECTOR(1536),
    content_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_journal_embeddings_content_hash
    ON journal_embeddings (content_hash);

-- =============================================================================
-- Conversation history + chat context
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    slug TEXT NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    tags TEXT[] DEFAULT '{}'::text[],
    status TEXT NOT NULL DEFAULT 'active',
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    turn_count INTEGER NOT NULL DEFAULT 0,
    summary_vec VECTOR(1536),
    archived_at TIMESTAMPTZ,
    CONSTRAINT conversation_sessions_user_slug_unique UNIQUE (user_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_status_last_active
    ON conversation_sessions (user_id, status, last_active_at DESC);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    tone TEXT,
    archetype TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    person_id UUID REFERENCES persons(id) ON DELETE SET NULL,
    reply TEXT,
    context_version INTEGER NOT NULL DEFAULT 1,
    queued_jobs JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT DEFAULT 'text'
);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_created
    ON conversation_turns (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_user_created
    ON conversation_turns (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS session_summaries (
    session_id UUID PRIMARY KEY REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    summary TEXT NOT NULL DEFAULT '',
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    turn_count_at_summary INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS conversation_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    last_emotion TEXT,
    dominant_theme TEXT,
    last_tone TEXT,
    clarity_level DOUBLE PRECISION,
    energy_level DOUBLE PRECISION,
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT conversation_state_person_unique UNIQUE (person_id)
);

CREATE TABLE IF NOT EXISTS persona_modes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(id) ON DELETE CASCADE,
    mode_name TEXT,
    activation_score DOUBLE PRECISION DEFAULT 0.0,
    last_activated TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_persona_modes_person_last_activated
    ON persona_modes (person_id, last_activated DESC);

CREATE TABLE IF NOT EXISTS theme_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(id) ON DELETE CASCADE,
    theme TEXT NOT NULL,
    rhythm_state JSONB DEFAULT '{}'::jsonb,
    emotional_state JSONB DEFAULT '{}'::jsonb,
    clarity_score DOUBLE PRECISION DEFAULT 0.0,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_theme_states_person_updated
    ON theme_states (person_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_theme_states_person_theme
    ON theme_states (person_id, theme);

CREATE TABLE IF NOT EXISTS planner_context_cache (
    person_id UUID PRIMARY KEY REFERENCES persons(id) ON DELETE CASCADE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS context_recalls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    turn_id UUID REFERENCES conversation_turns(id) ON DELETE SET NULL,
    thread_id UUID,
    stitched_summary TEXT,
    compact JSONB DEFAULT '{}'::jsonb,
    vectors JSONB DEFAULT '{}'::jsonb,
    signals JSONB DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT context_recalls_person_turn_unique UNIQUE (person_id, turn_id)
);

CREATE INDEX IF NOT EXISTS idx_context_recalls_person_created
    ON context_recalls (person_id, created_at DESC);

CREATE TABLE IF NOT EXISTS thread_continuity_markers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL,
    continuity_hint TEXT,
    persona_stability JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_turn_id UUID REFERENCES conversation_turns(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT thread_continuity_markers_person_thread_unique UNIQUE (person_id, thread_id)
);

CREATE INDEX IF NOT EXISTS idx_thread_continuity_markers_person_updated
    ON thread_continuity_markers (person_id, updated_at DESC);

-- =============================================================================
-- Person model + continuity state
-- =============================================================================

CREATE TABLE IF NOT EXISTS personal_model (
    person_id UUID PRIMARY KEY REFERENCES persons(id) ON DELETE CASCADE,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    body_state JSONB DEFAULT '{}'::jsonb,
    mind_state JSONB DEFAULT '{}'::jsonb,
    emotion_state JSONB DEFAULT '{}'::jsonb,
    goals_state JSONB DEFAULT '{}'::jsonb,
    rhythm_state JSONB DEFAULT '{}'::jsonb,
    short_term JSONB DEFAULT '{}'::jsonb,
    long_term JSONB DEFAULT '{}'::jsonb,
    summary_text TEXT,
    last_seen TIMESTAMPTZ DEFAULT now(),
    last_reflection TIMESTAMPTZ,
    coherence NUMERIC DEFAULT 0,
    short_term_vector JSONB DEFAULT '{}'::jsonb,
    emotion TEXT,
    relationship_state JSONB,
    soul_state JSONB DEFAULT '{"longing": [], "aversions": [], "confidence": 0.0, "updated_at": null, "commitments": [], "core_values": [], "light_patterns": [], "identity_themes": [], "shadow_patterns": []}'::jsonb,
    soul_vector VECTOR(1536),
    soul_shadow JSONB DEFAULT '{}'::jsonb,
    soul_light JSONB DEFAULT '{}'::jsonb,
    soul_conflicts JSONB DEFAULT '{}'::jsonb,
    soul_friction JSONB DEFAULT '{}'::jsonb,
    emotion_soul_rhythm_state JSONB DEFAULT '{}'::jsonb,
    identity_momentum_state JSONB DEFAULT '{}'::jsonb,
    internal_decision_graph JSONB DEFAULT '{}'::jsonb,
    identity_timeline JSONB DEFAULT '{}'::jsonb,
    persona_evolution_state JSONB DEFAULT '{}'::jsonb,
    coherence_report JSONB DEFAULT '{}'::jsonb,
    narrative_arcs JSONB DEFAULT '[]'::jsonb,
    pattern_sense JSONB DEFAULT '{}'::jsonb,
    inner_dialogue_state JSONB DEFAULT '{}'::jsonb,
    identity_state JSONB DEFAULT '{}'::jsonb,
    conflict_state JSONB DEFAULT '{}'::jsonb,
    coherence_state JSONB DEFAULT '{}'::jsonb,
    forecast_state JSONB DEFAULT '{}'::jsonb,
    tone_state JSONB DEFAULT '{}'::jsonb,
    nudge_state JSONB DEFAULT '{}'::jsonb,
    empathy_state JSONB DEFAULT '{}'::jsonb,
    daily_reflection_state JSONB DEFAULT '{}'::jsonb,
    closure_state JSONB DEFAULT '{}'::jsonb,
    morning_preview_state JSONB DEFAULT '{}'::jsonb,
    morning_ask_state JSONB DEFAULT '{}'::jsonb,
    morning_momentum_state JSONB DEFAULT '{}'::jsonb,
    micro_momentum_state JSONB DEFAULT '{}'::jsonb,
    micro_recovery_state JSONB DEFAULT '{}'::jsonb,
    focus_path_state JSONB DEFAULT '{}'::jsonb,
    mini_flow_state JSONB DEFAULT '{}'::jsonb,
    mini_flow_rhythm_slot TEXT,
    longitudinal_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    alignment_state JSONB DEFAULT '{}'::jsonb,
    rhythm_soul_state JSONB DEFAULT '{}'::jsonb,
    soul_narrative JSONB DEFAULT '{}'::jsonb,
    operating_system JSONB,
    life_context JSONB,
    decision_profile JSONB,
    onboarding_source TEXT,
    onboarding_phase TEXT,
    phase1_completed_at TIMESTAMPTZ,
    phase2a_completed_at TIMESTAMPTZ,
    phase2b_completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS session_continuity (
    person_id UUID PRIMARY KEY REFERENCES persons(id) ON DELETE CASCADE,
    last_emotion TEXT,
    last_interaction_ts TIMESTAMPTZ DEFAULT now(),
    engagement_level NUMERIC DEFAULT 0.5,
    reflection_pending BOOLEAN DEFAULT false,
    clarity_level DOUBLE PRECISION DEFAULT 0
);

-- =============================================================================
-- Continuity MVP schema
-- =============================================================================

CREATE TABLE IF NOT EXISTS continuity_surface_policy (
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT false,
    exclusions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (person_id, scope)
);

CREATE TABLE IF NOT EXISTS continuity_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    anchor TEXT NOT NULL,
    facets JSONB NOT NULL DEFAULT '[]'::jsonb,
    entities JSONB NOT NULL DEFAULT '[]'::jsonb,
    scalar DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT continuity_labels_source_unique UNIQUE (person_id, source_type, source_id)
);

CREATE INDEX IF NOT EXISTS idx_continuity_labels_anchor
    ON continuity_labels (person_id, anchor, source_type, created_at DESC);

CREATE TABLE IF NOT EXISTS deep_reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    topic_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed')),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    inputs_hash TEXT NOT NULL DEFAULT '',
    result_json JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS deep_reflections_person_topic_created_idx
    ON deep_reflections (person_id, topic_key, created_at DESC);

CREATE TABLE IF NOT EXISTS continuity_topic_correlations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    topic_key_a TEXT NOT NULL,
    topic_key_b TEXT NOT NULL,
    combined_score DOUBLE PRECISION NOT NULL,
    temporal_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    semantic_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    facet_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    directional_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    correlation_types JSONB NOT NULL DEFAULT '[]'::jsonb,
    shared_facets JSONB NOT NULL DEFAULT '[]'::jsonb,
    overlap_windows JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_window_start TIMESTAMPTZ,
    source_window_end TIMESTAMPTZ,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT continuity_topic_corr_pair_unique UNIQUE (person_id, topic_key_a, topic_key_b),
    CONSTRAINT continuity_topic_corr_pair_order CHECK (topic_key_a < topic_key_b)
);

CREATE INDEX IF NOT EXISTS idx_continuity_topic_corr_person_score
    ON continuity_topic_correlations (person_id, combined_score DESC, computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_continuity_topic_corr_person_topic_a
    ON continuity_topic_correlations (person_id, topic_key_a, computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_continuity_topic_corr_person_topic_b
    ON continuity_topic_correlations (person_id, topic_key_b, computed_at DESC);

CREATE TABLE IF NOT EXISTS continuity_life_dimensions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,
    signal_level DOUBLE PRECISION NOT NULL,
    signal_direction TEXT NOT NULL,
    affected_topics TEXT[] NOT NULL DEFAULT '{}'::text[],
    evidence_summary TEXT,
    signal_markers JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT continuity_life_dimensions_unique UNIQUE (person_id, dimension),
    CONSTRAINT continuity_life_dimensions_dimension_check
        CHECK (dimension IN ('time_availability', 'financial_pressure', 'emotional_bandwidth')),
    CONSTRAINT continuity_life_dimensions_direction_check
        CHECK (signal_direction IN ('pressured', 'neutral', 'resourced'))
);

CREATE INDEX IF NOT EXISTS idx_continuity_life_dimensions_person
    ON continuity_life_dimensions (person_id, computed_at DESC);

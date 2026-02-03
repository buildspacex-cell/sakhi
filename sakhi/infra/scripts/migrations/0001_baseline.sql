-- Sakhi Database Baseline Migration
-- Generated from live production database on 2026-02-03
-- 179 tables

-- Required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- Table: agent_actions
CREATE TABLE IF NOT EXISTS agent_actions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    person_id text NOT NULL,
    action_type text NOT NULL,
    parameters jsonb DEFAULT '{}'::jsonb,
    requires_approval boolean DEFAULT false,
    approved_at timestamp with time zone,
    sequence integer DEFAULT 0,
    status text NOT NULL DEFAULT 'pending'::text,
    sent_at timestamp with time zone,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    result jsonb,
    retry_count integer DEFAULT 0,
    error_message text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: agent_approval_history
CREATE TABLE IF NOT EXISTS agent_approval_history (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    action_type text NOT NULL,
    risk_level text NOT NULL,
    decision text NOT NULL,
    selected_option text,
    user_comment text,
    request_created_at timestamp with time zone NOT NULL,
    decision_at timestamp with time zone NOT NULL DEFAULT now(),
    response_time_seconds double precision,
    task_type text,
    context_summary text
);

-- Table: agent_approval_preferences
CREATE TABLE IF NOT EXISTS agent_approval_preferences (
    person_id uuid NOT NULL,
    auto_approve_actions text[] DEFAULT '{}'::text[],
    approve_medium_risk boolean DEFAULT false,
    notify_on_critical boolean DEFAULT true,
    notification_channel text DEFAULT 'chat'::text,
    default_timeout_seconds integer DEFAULT 300,
    learn_from_history boolean DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: agent_approval_requests
CREATE TABLE IF NOT EXISTS agent_approval_requests (
    request_id text NOT NULL,
    session_id text NOT NULL,
    task_id text NOT NULL,
    person_id uuid NOT NULL,
    action_type text NOT NULL,
    action_parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    action_description text NOT NULL,
    risk_level text NOT NULL,
    status text NOT NULL DEFAULT 'pending'::text,
    context_summary text,
    why_approval_needed text,
    if_approved text,
    if_rejected text,
    options jsonb DEFAULT '[]'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    expires_at timestamp with time zone,
    resolved_at timestamp with time zone,
    resolved_by text,
    screenshot_id text,
    screenshot_url text
);

-- Table: agent_screenshots
CREATE TABLE IF NOT EXISTS agent_screenshots (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid,
    agent_id uuid NOT NULL,
    person_id uuid NOT NULL,
    storage_path text NOT NULL,
    storage_bucket text DEFAULT 'screenshots'::text,
    width integer,
    height integer,
    format text DEFAULT 'png'::text,
    trigger text,
    preceding_action_id uuid,
    analysis jsonb,
    analyzed_at timestamp with time zone,
    captured_at timestamp with time zone NOT NULL DEFAULT now(),
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: agent_sessions
CREATE TABLE IF NOT EXISTS agent_sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id text NOT NULL,
    agent_id uuid NOT NULL,
    task_description text,
    status text NOT NULL DEFAULT 'active'::text,
    current_step integer DEFAULT 0,
    total_steps integer,
    actions_executed integer DEFAULT 0,
    timeout_at timestamp with time zone,
    started_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    actions_failed integer DEFAULT 0
);

-- Table: agent_task_plans
CREATE TABLE IF NOT EXISTS agent_task_plans (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    session_id uuid,
    task_type text NOT NULL,
    task_description text NOT NULL,
    steps jsonb NOT NULL DEFAULT '[]'::jsonb,
    context_used jsonb DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'planned'::text,
    current_step_index integer DEFAULT 0,
    result jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);

-- Table: agent_versions
CREATE TABLE IF NOT EXISTS agent_versions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    agent_type text NOT NULL,
    platform text NOT NULL,
    architecture text DEFAULT 'universal'::text,
    version text NOT NULL,
    download_url text,
    checksum text,
    file_size_bytes bigint,
    is_mandatory boolean DEFAULT false,
    release_notes text,
    min_required_version text,
    status text DEFAULT 'active'::text,
    released_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);

-- Table: analytics_cache
CREATE TABLE IF NOT EXISTS analytics_cache (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    metric text NOT NULL,
    value double precision,
    period text DEFAULT 'weekly'::text,
    computed_at timestamp with time zone DEFAULT now()
);

-- Table: auth_users
CREATE TABLE IF NOT EXISTS auth_users (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    supabase_user_id uuid,
    email text NOT NULL,
    full_name text,
    avatar_url text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    last_sign_in_at timestamp with time zone,
    onboarding_completed_at timestamp with time zone,
    deleted_at timestamp with time zone
);

-- Table: behavior_log
CREATE TABLE IF NOT EXISTS behavior_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    behavior_type text NOT NULL,
    behavior_name text NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    dosha_effect text,
    effect_direction text,
    source_text text,
    source_type text DEFAULT 'conversation'::text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    time_of_day text,
    source text DEFAULT 'inferred'::text,
    related_entry_id text,
    intensity double precision
);

-- Table: body_state_history
CREATE TABLE IF NOT EXISTS body_state_history (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    body_state jsonb NOT NULL,
    computed_at timestamp with time zone DEFAULT now(),
    overall_score double precision,
    vata_score double precision,
    pitta_score double precision,
    kapha_score double precision,
    ojas_level double precision,
    sleep_quality double precision,
    energy_level double precision
);

-- Table: brain_goals_themes
CREATE TABLE IF NOT EXISTS brain_goals_themes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    cluster_title text,
    cluster_vector vector(1536),
    supporting_entry_ids uuid[],
    confidence double precision,
    time_window text,
    emotional_tone jsonb,
    value_mapping jsonb,
    identity_alignment double precision,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: coherence_cache
CREATE TABLE IF NOT EXISTS coherence_cache (
    person_id uuid NOT NULL,
    coherence_state jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: collective_patterns
CREATE TABLE IF NOT EXISTS collective_patterns (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    pattern_type text NOT NULL,
    mean_vector vector(1536),
    std_dev_vector vector(1536),
    support_count integer NOT NULL DEFAULT 0,
    last_updated timestamp with time zone DEFAULT now(),
    metadata jsonb DEFAULT '{}'::jsonb
);

-- Table: context_recalls
CREATE TABLE IF NOT EXISTS context_recalls (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    turn_id uuid,
    thread_id uuid,
    stitched_summary text,
    compact jsonb DEFAULT '{}'::jsonb,
    vectors jsonb DEFAULT '{}'::jsonb,
    signals jsonb DEFAULT '{}'::jsonb,
    confidence double precision DEFAULT 0.5,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: conversation_media
CREATE TABLE IF NOT EXISTS conversation_media (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    media_id uuid NOT NULL,
    session_id text,
    entry_id uuid,
    turn_index integer,
    role text NOT NULL DEFAULT 'user'::text,
    purpose text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: conversation_sessions
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    slug text NOT NULL,
    title text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    tags text[] DEFAULT '{}'::text[],
    status text NOT NULL DEFAULT 'active'::text,
    last_active_at timestamp with time zone NOT NULL DEFAULT now(),
    turn_count integer NOT NULL DEFAULT 0,
    summary_vec vector(1536),
    archived_at timestamp with time zone
);

-- Table: conversation_state
CREATE TABLE IF NOT EXISTS conversation_state (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    last_emotion text,
    dominant_theme text,
    last_tone text,
    clarity_level double precision,
    energy_level double precision,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: conversation_suggestions
CREATE TABLE IF NOT EXISTS conversation_suggestions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    suggestion text NOT NULL,
    style text,
    confidence double precision,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: conversation_turns
CREATE TABLE IF NOT EXISTS conversation_turns (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    session_id uuid NOT NULL,
    role text NOT NULL,
    text text NOT NULL,
    tone text,
    archetype text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    person_id uuid,
    reply text,
    context_version integer NOT NULL DEFAULT 1,
    queued_jobs jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    source text DEFAULT 'text'::text
);

-- Table: coordination_messages
CREATE TABLE IF NOT EXISTS coordination_messages (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    thread_id uuid NOT NULL,
    sender_entity_id uuid NOT NULL,
    sender_type text NOT NULL DEFAULT 'sakhi'::text,
    message_type text NOT NULL,
    content jsonb NOT NULL,
    requires_response boolean DEFAULT false,
    response_deadline timestamp with time zone,
    read_at timestamp with time zone,
    responded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: coordination_threads
CREATE TABLE IF NOT EXISTS coordination_threads (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    initiator_entity_id uuid NOT NULL,
    recipient_entity_id uuid NOT NULL,
    coordination_type text NOT NULL,
    subject text,
    context jsonb NOT NULL DEFAULT '{}'::jsonb,
    proposed_options jsonb,
    status text NOT NULL DEFAULT 'open'::text,
    outcome jsonb,
    related_event_id uuid,
    related_transaction_id uuid,
    relationship_context jsonb,
    priority text DEFAULT 'normal'::text,
    expires_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: crystallization_log
CREATE TABLE IF NOT EXISTS crystallization_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    crystallized_pattern_id uuid,
    pattern_type text NOT NULL,
    pattern_value text NOT NULL,
    occurrence_count integer,
    distinct_days integer,
    confidence double precision,
    span_days integer,
    threshold_config jsonb,
    evidence_ids uuid[],
    action text,
    crystallized_at timestamp with time zone DEFAULT now()
);

-- Table: crystallized_patterns
CREATE TABLE IF NOT EXISTS crystallized_patterns (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    pattern_type text NOT NULL,
    pattern_value text NOT NULL,
    sub_topic text,
    summary text,
    constitution_relevance text,
    evidence_ids uuid[] DEFAULT '{}'::uuid[],
    evidence_snippets jsonb DEFAULT '[]'::jsonb,
    mention_count integer NOT NULL DEFAULT 0,
    distinct_days integer NOT NULL DEFAULT 0,
    confidence double precision NOT NULL DEFAULT 0.0,
    threshold_met_at timestamp with time zone,
    trajectory text DEFAULT 'stable'::text,
    trajectory_data jsonb DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'emerging'::text,
    first_seen timestamp with time zone NOT NULL DEFAULT now(),
    last_seen timestamp with time zone NOT NULL DEFAULT now(),
    crystallized_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: daily_alignment_cache
CREATE TABLE IF NOT EXISTS daily_alignment_cache (
    person_id uuid NOT NULL,
    alignment_map jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: daily_closure_cache
CREATE TABLE IF NOT EXISTS daily_closure_cache (
    id bigint NOT NULL,
    person_id uuid,
    closure_date date NOT NULL,
    completed jsonb DEFAULT '[]'::jsonb,
    pending jsonb DEFAULT '[]'::jsonb,
    signals jsonb DEFAULT '{}'::jsonb,
    summary text DEFAULT ''::text,
    generated_at timestamp with time zone DEFAULT now()
);

-- Table: daily_reflection_cache
CREATE TABLE IF NOT EXISTS daily_reflection_cache (
    person_id uuid NOT NULL,
    reflection_date date NOT NULL,
    summary jsonb NOT NULL,
    generated_at timestamp with time zone DEFAULT now()
);

-- Table: debug_traces
CREATE TABLE IF NOT EXISTS debug_traces (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    trace_id text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    flow text NOT NULL,
    payload jsonb NOT NULL,
    human_narrative text,
    plain_layers jsonb,
    finished_at timestamp with time zone DEFAULT now(),
    success boolean DEFAULT false,
    summary jsonb DEFAULT '{}'::jsonb
);

-- Table: device_link_codes
CREATE TABLE IF NOT EXISTS device_link_codes (
    code text NOT NULL,
    device_id text NOT NULL,
    platform text NOT NULL,
    architecture text,
    agent_type text NOT NULL DEFAULT 'desktop'::text,
    agent_name text,
    status text NOT NULL DEFAULT 'pending'::text,
    person_id uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    expires_at timestamp with time zone NOT NULL DEFAULT (now() + '00:10:00'::interval),
    confirmed_at timestamp with time zone
);

-- Table: elemental_signal_stm
CREATE TABLE IF NOT EXISTS elemental_signal_stm (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    source_signal_id uuid NOT NULL,
    source_type text NOT NULL,
    dimension text NOT NULL,
    earth numeric(4,3) NOT NULL DEFAULT 0,
    water numeric(4,3) NOT NULL DEFAULT 0,
    fire numeric(4,3) NOT NULL DEFAULT 0,
    air numeric(4,3) NOT NULL DEFAULT 0,
    ether numeric(4,3) NOT NULL DEFAULT 0,
    confidence numeric(4,3) NOT NULL DEFAULT 1.0,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    expires_at timestamp with time zone NOT NULL,
    magnitude numeric(6,3) NOT NULL DEFAULT 0
);

-- Table: elemental_summary_weekly
CREATE TABLE IF NOT EXISTS elemental_summary_weekly (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    week_start date NOT NULL,
    elements jsonb DEFAULT '{}'::jsonb,
    dosha_balance jsonb DEFAULT '{}'::jsonb,
    signals_count integer DEFAULT 0,
    confidence double precision DEFAULT 0.5,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: events
CREATE TABLE IF NOT EXISTS events (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    type text NOT NULL,
    v integer NOT NULL DEFAULT 1,
    ts timestamp with time zone NOT NULL DEFAULT now(),
    idempotency_key text,
    payload jsonb NOT NULL,
    occurred_at timestamp with time zone NOT NULL DEFAULT now(),
    event_type text NOT NULL,
    response jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: facts
CREATE TABLE IF NOT EXISTS facts (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    scope text NOT NULL,
    key text NOT NULL,
    value jsonb NOT NULL DEFAULT '{}'::jsonb,
    confidence double precision DEFAULT 0.5,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    embedding vector(1536)
);

-- Table: focus_events
CREATE TABLE IF NOT EXISTS focus_events (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    ts timestamp with time zone NOT NULL DEFAULT now(),
    event_type text NOT NULL,
    content jsonb NOT NULL DEFAULT '{}'::jsonb,
    rhythm_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    task_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    emotion_state jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- Table: focus_path_cache
CREATE TABLE IF NOT EXISTS focus_path_cache (
    id bigint NOT NULL,
    person_id uuid,
    path_date date NOT NULL,
    anchor_step text DEFAULT ''::text,
    progress_step text DEFAULT ''::text,
    closure_step text DEFAULT ''::text,
    intent_source text DEFAULT ''::text,
    generated_at timestamp with time zone DEFAULT now()
);

-- Table: focus_sessions
CREATE TABLE IF NOT EXISTS focus_sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    task_id uuid,
    mode text DEFAULT 'deep'::text,
    start_time timestamp with time zone NOT NULL DEFAULT now(),
    end_time timestamp with time zone,
    estimated_duration integer,
    actual_duration integer,
    completion_score numeric,
    session_quality jsonb NOT NULL DEFAULT '{}'::jsonb,
    session_start_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'active'::text,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: forecast_cache
CREATE TABLE IF NOT EXISTS forecast_cache (
    person_id uuid NOT NULL,
    forecast_state jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: goal_history
CREATE TABLE IF NOT EXISTS goal_history (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    goal_id uuid,
    person_id uuid,
    previous_title text,
    previous_description text,
    revised_title text,
    revised_description text,
    reason text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: goals
CREATE TABLE IF NOT EXISTS goals (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    parent_goal_id uuid,
    title text,
    description text,
    horizon text,
    status text,
    progress numeric DEFAULT 0,
    evolution_score double precision DEFAULT 0.0,
    last_revised timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    type text DEFAULT 'goal'::text,
    priority integer DEFAULT 0,
    due_at timestamp with time zone,
    meta jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone
);

-- Table: growth_daily_checkins
CREATE TABLE IF NOT EXISTS growth_daily_checkins (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    checkin_date date NOT NULL DEFAULT CURRENT_DATE,
    energy numeric,
    mood text,
    reflection text,
    plan_adjustment jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: growth_habit_logs
CREATE TABLE IF NOT EXISTS growth_habit_logs (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    habit_id uuid NOT NULL,
    person_id uuid NOT NULL,
    logged_at timestamp with time zone NOT NULL DEFAULT now(),
    micro_score numeric NOT NULL DEFAULT 0.2,
    mood text,
    note text,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- Table: growth_habits
CREATE TABLE IF NOT EXISTS growth_habits (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    label text NOT NULL,
    cadence jsonb NOT NULL DEFAULT '{}'::jsonb,
    intent_source text,
    streak_count integer NOT NULL DEFAULT 0,
    micro_progress numeric NOT NULL DEFAULT 0.0,
    confidence numeric NOT NULL DEFAULT 0.5,
    last_logged timestamp with time zone,
    active boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: growth_task_confidence_events
CREATE TABLE IF NOT EXISTS growth_task_confidence_events (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    task_id uuid,
    task_label text,
    confidence_before numeric,
    confidence_after numeric,
    delta numeric,
    source text,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: health_data_sync
CREATE TABLE IF NOT EXISTS health_data_sync (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    source text NOT NULL,
    data_type text NOT NULL,
    data jsonb NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    synced_at timestamp with time zone DEFAULT now(),
    processed boolean DEFAULT false,
    processed_at timestamp with time zone
);

-- Table: identity_drift_cache
CREATE TABLE IF NOT EXISTS identity_drift_cache (
    person_id uuid NOT NULL,
    identity_state jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: inner_conflict_cache
CREATE TABLE IF NOT EXISTS inner_conflict_cache (
    person_id uuid NOT NULL,
    conflict_state jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: inner_dialogue_cache
CREATE TABLE IF NOT EXISTS inner_dialogue_cache (
    person_id uuid NOT NULL,
    dialogue jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: insight
CREATE TABLE IF NOT EXISTS insight (
    id text NOT NULL,
    person_id uuid NOT NULL,
    from_ids text[] NOT NULL,
    kind text NOT NULL,
    message text NOT NULL,
    why jsonb,
    actions jsonb,
    confidence numeric DEFAULT 0.6,
    ts timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: insights_queue
CREATE TABLE IF NOT EXISTS insights_queue (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    insight jsonb NOT NULL,
    priority text DEFAULT 'medium'::text,
    timing_hint text DEFAULT 'next_check_in'::text,
    delivered boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: intent_evolution
CREATE TABLE IF NOT EXISTS intent_evolution (
    person_id uuid NOT NULL,
    intent_name text NOT NULL,
    strength double precision DEFAULT 0,
    emotional_alignment double precision DEFAULT 0,
    trend text DEFAULT 'stable'::text,
    last_seen timestamp with time zone DEFAULT now(),
    first_seen timestamp with time zone DEFAULT now()
);

-- Table: intents
CREATE TABLE IF NOT EXISTS intents (
    id bigint NOT NULL,
    user_id uuid NOT NULL,
    source_entry_id uuid,
    title text NOT NULL,
    raw_input text,
    intent_type text NOT NULL,
    domain text,
    timeline text NOT NULL DEFAULT 'none'::text,
    target_date date,
    priority smallint,
    status text NOT NULL DEFAULT 'draft'::text,
    clarity_score numeric DEFAULT 0.0,
    user_permission boolean DEFAULT false,
    proposed_plan jsonb,
    context_snapshot jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: intervention_checkins
CREATE TABLE IF NOT EXISTS intervention_checkins (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    plan_id uuid NOT NULL,
    scheduled_date date NOT NULL,
    status text DEFAULT 'pending'::text,
    completed_count integer DEFAULT 0,
    notes text,
    mood_before double precision,
    mood_after double precision,
    checked_in_at timestamp with time zone,
    nudge_sent boolean DEFAULT false,
    nudge_sent_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: intervention_nudges
CREATE TABLE IF NOT EXISTS intervention_nudges (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    plan_id uuid,
    checkin_id uuid,
    nudge_type text NOT NULL,
    message text NOT NULL,
    channel text DEFAULT 'chat'::text,
    sent_at timestamp with time zone DEFAULT now(),
    read_at timestamp with time zone,
    acted_on boolean DEFAULT false,
    acted_at timestamp with time zone
);

-- Table: intervention_outcomes
CREATE TABLE IF NOT EXISTS intervention_outcomes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    intervention_type text NOT NULL,
    intervention_name text NOT NULL,
    occurred_at timestamp with time zone DEFAULT now(),
    was_effective boolean,
    effectiveness_score double precision,
    symptom_addressed text,
    related_dosha text,
    notes text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: intervention_plans
CREATE TABLE IF NOT EXISTS intervention_plans (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    intervention_type text NOT NULL,
    intervention_name text NOT NULL,
    description text,
    schedule_type text NOT NULL DEFAULT 'daily'::text,
    schedule_days int4[],
    target_per_day integer DEFAULT 1,
    start_date date NOT NULL DEFAULT CURRENT_DATE,
    end_date date,
    duration_days integer,
    target_symptom text,
    target_dosha text,
    baseline_severity double precision,
    status text DEFAULT 'active'::text,
    total_scheduled integer DEFAULT 0,
    total_completed integer DEFAULT 0,
    current_streak integer DEFAULT 0,
    longest_streak integer DEFAULT 0,
    notes text,
    recommendation_id uuid,
    conversation_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: journal_embeddings
CREATE TABLE IF NOT EXISTS journal_embeddings (
    entry_id uuid NOT NULL,
    model text NOT NULL DEFAULT 'text-embedding-3-small'::text,
    embedding vector(1536),
    created_at timestamp with time zone DEFAULT now(),
    embedding_vec vector(1536),
    content_hash text
);

-- Table: journal_entries
CREATE TABLE IF NOT EXISTS journal_entries (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    raw_encrypted bytea,
    cleaned text,
    facets jsonb NOT NULL DEFAULT '{}'::jsonb,
    salience real NOT NULL DEFAULT 0,
    ts timestamp with time zone NOT NULL DEFAULT now(),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    content text,
    title text,
    fts tsvector,
    raw text,
    encrypted_preview text,
    facets_v2 jsonb DEFAULT '{}'::jsonb,
    cleaned_tsv tsvector,
    narrative jsonb NOT NULL DEFAULT '{}'::jsonb,
    debug_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    layer text,
    tags text[] DEFAULT '{}'::text[],
    source_ref jsonb DEFAULT '{}'::jsonb,
    mood text,
    person_id uuid,
    processing_state text NOT NULL DEFAULT 'queued'::text,
    processing_attempts integer NOT NULL DEFAULT 0,
    processed_at timestamp with time zone,
    processing_error jsonb,
    ack_text text,
    worker_enrichment jsonb,
    input_type text,
    client_context jsonb DEFAULT '{}'::jsonb,
    language text,
    timezone text,
    user_tags text[] DEFAULT '{}'::text[]
);

-- Table: journal_inference
CREATE TABLE IF NOT EXISTS journal_inference (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    entry_id uuid NOT NULL,
    container text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    confidence numeric,
    inference_type text NOT NULL,
    source text,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: journal_links
CREATE TABLE IF NOT EXISTS journal_links (
    src_id uuid NOT NULL,
    dst_id uuid NOT NULL,
    strength numeric NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: journal_themes
CREATE TABLE IF NOT EXISTS journal_themes (
    id bigint NOT NULL,
    user_id uuid NOT NULL,
    theme text NOT NULL,
    time_window text NOT NULL,
    metrics jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    description text,
    domain text,
    examples jsonb
);

-- Table: journey_cache
CREATE TABLE IF NOT EXISTS journey_cache (
    person_id uuid NOT NULL,
    scope text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: learning_runs
CREATE TABLE IF NOT EXISTS learning_runs (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    run_type text NOT NULL,
    trigger_reason text,
    behaviors_processed integer DEFAULT 0,
    symptoms_processed integer DEFAULT 0,
    patterns_detected integer DEFAULT 0,
    patterns_strengthened integer DEFAULT 0,
    preferences_updated integer DEFAULT 0,
    started_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    duration_ms integer,
    status text DEFAULT 'running'::text,
    error_message text
);

-- Table: long_running_missions
CREATE TABLE IF NOT EXISTS long_running_missions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    title text NOT NULL,
    description text,
    category text,
    success_criteria jsonb,
    plan_document text,
    target_end_date date,
    actual_end_date date,
    status text DEFAULT 'active'::text,
    health text DEFAULT 'on_track'::text,
    strategy_notes text,
    lessons_learned jsonb,
    progress_pct integer DEFAULT 0,
    metrics jsonb,
    conversation_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: media_attachments
CREATE TABLE IF NOT EXISTS media_attachments (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id text NOT NULL,
    media_type text NOT NULL,
    mime_type text NOT NULL,
    filename text,
    file_size_bytes integer,
    storage_provider text NOT NULL DEFAULT 'local'::text,
    storage_path text NOT NULL,
    thumbnail_path text,
    extracted_text text,
    description text,
    analysis jsonb DEFAULT '{}'::jsonb,
    source text,
    context text,
    status text DEFAULT 'pending'::text,
    processed_at timestamp with time zone,
    error_message text,
    width integer,
    height integer,
    duration_seconds double precision,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: memory_context_cache
CREATE TABLE IF NOT EXISTS memory_context_cache (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    window_kind text NOT NULL DEFAULT 'default'::text,
    entries jsonb NOT NULL DEFAULT '[]'::jsonb,
    rhythm_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    persona_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    task_window jsonb NOT NULL DEFAULT '[]'::jsonb,
    version integer NOT NULL DEFAULT 1,
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    merged_context_vector vector(1536)
);

-- Table: memory_edges
CREATE TABLE IF NOT EXISTS memory_edges (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    from_node uuid,
    to_node uuid,
    relation text,
    weight double precision DEFAULT 0.5,
    updated_at timestamp with time zone DEFAULT now(),
    relevance double precision DEFAULT 0.5,
    created_at timestamp with time zone DEFAULT now(),
    evidence jsonb DEFAULT '{}'::jsonb,
    occurrence_count integer DEFAULT 1
);

-- Table: memory_episodic
CREATE TABLE IF NOT EXISTS memory_episodic (
    id uuid NOT NULL,
    user_id text NOT NULL,
    record jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    soul jsonb DEFAULT '{}'::jsonb,
    soul_shadow jsonb DEFAULT '{}'::jsonb,
    soul_light jsonb DEFAULT '{}'::jsonb,
    soul_conflict jsonb DEFAULT '{}'::jsonb,
    soul_friction jsonb DEFAULT '{}'::jsonb,
    emotion_loop jsonb DEFAULT '{}'::jsonb,
    content_hash text,
    vector_vec vector(1536),
    context_tags jsonb DEFAULT '[]'::jsonb,
    entry_id uuid,
    person_id uuid,
    triage jsonb,
    time_scope timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now(),
    text text,
    rhythm_state jsonb DEFAULT '{}'::jsonb,
    emotional_state jsonb DEFAULT '{}'::jsonb,
    ts timestamp with time zone DEFAULT now(),
    state_vector jsonb,
    guna_vector jsonb
);

-- Table: memory_monthly_recaps
CREATE TABLE IF NOT EXISTS memory_monthly_recaps (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    month_scope daterange NOT NULL,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    highlights text,
    top_themes jsonb NOT NULL DEFAULT '[]'::jsonb,
    chapter_hint text,
    drift_score numeric NOT NULL DEFAULT 0.0,
    compression jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: memory_nodes
CREATE TABLE IF NOT EXISTS memory_nodes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    node_kind text,
    label text,
    data jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    weight double precision DEFAULT 0.5,
    updated_at timestamp with time zone DEFAULT now(),
    last_referenced_at timestamp with time zone DEFAULT now()
);

-- Table: memory_semantic_rollups
CREATE TABLE IF NOT EXISTS memory_semantic_rollups (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    source_id uuid NOT NULL,
    source_kind text NOT NULL,
    semantic_summary text NOT NULL,
    strength numeric NOT NULL DEFAULT 0.0,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: memory_short_term
CREATE TABLE IF NOT EXISTS memory_short_term (
    id uuid NOT NULL,
    user_id text NOT NULL,
    record jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    soul jsonb DEFAULT '{}'::jsonb,
    soul_shadow jsonb DEFAULT '{}'::jsonb,
    soul_light jsonb DEFAULT '{}'::jsonb,
    content_hash text,
    vector_vec vector(1536),
    expires_at timestamp with time zone NOT NULL DEFAULT (now() + ((COALESCE((NULLIF(current_setting('sakhi.stm_ttl_days'::text, true), ''::text))::integer, 14))::double precision * '1 day'::interval)),
    entry_id uuid,
    text text,
    layer text,
    triage jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now(),
    person_id text
);

-- Table: memory_strength_events
CREATE TABLE IF NOT EXISTS memory_strength_events (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    event_kind text NOT NULL,
    target text NOT NULL,
    weight numeric NOT NULL DEFAULT 0.0,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: memory_theme_drift_events
CREATE TABLE IF NOT EXISTS memory_theme_drift_events (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    horizon text NOT NULL,
    from_theme text,
    to_theme text,
    drift_score numeric NOT NULL DEFAULT 0.0,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: memory_weekly_signals
CREATE TABLE IF NOT EXISTS memory_weekly_signals (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    week_start date NOT NULL,
    week_end date NOT NULL,
    episodic_stats jsonb NOT NULL DEFAULT '{}'::jsonb,
    theme_stats jsonb NOT NULL DEFAULT '[]'::jsonb,
    contrast_stats jsonb NOT NULL DEFAULT '{}'::jsonb,
    delta_stats jsonb NOT NULL DEFAULT '{}'::jsonb,
    confidence numeric NOT NULL DEFAULT 0.0,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    weekly_contrast jsonb DEFAULT '{"count": 0, "positive_glimpses": []}'::jsonb,
    dimension_states jsonb DEFAULT '{"body": "flat", "mind": "flat", "work": "flat", "energy": "flat", "emotion": "flat"}'::jsonb,
    weekly_salience jsonb DEFAULT '{"items": [], "present": false}'::jsonb,
    weekly_body_notes jsonb DEFAULT '{"count": 0, "discomfort_hints": []}'::jsonb
);

-- Table: memory_weekly_summaries
CREATE TABLE IF NOT EXISTS memory_weekly_summaries (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    week_start date NOT NULL,
    week_end date NOT NULL,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    highlights text,
    top_themes jsonb NOT NULL DEFAULT '[]'::jsonb,
    drift_score numeric NOT NULL DEFAULT 0.0,
    semantic_notes jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: mesh_coordination
CREATE TABLE IF NOT EXISTS mesh_coordination (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL,
    initiator_sakhi_id uuid NOT NULL,
    target_sakhi_id uuid NOT NULL,
    coordination_type text NOT NULL DEFAULT 'scheduling'::text,
    event_type text,
    request_context text,
    timeframe_start timestamp with time zone,
    timeframe_end timestamp with time zone,
    preferred_duration_minutes integer,
    status text DEFAULT 'requested'::text,
    initiator_availability jsonb,
    target_availability jsonb,
    proposed_time timestamp with time zone,
    proposed_location text,
    proposed_location_data jsonb,
    proposal_reasoning text,
    initiator_response text,
    target_response text,
    initiator_event_id uuid,
    target_event_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone DEFAULT (now() + '7 days'::interval)
);

-- Table: mesh_endpoints
CREATE TABLE IF NOT EXISTS mesh_endpoints (
    sakhi_id text NOT NULL,
    person_id uuid NOT NULL,
    endpoint_url text NOT NULL,
    display_name text,
    public_key text,
    last_seen timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);

-- Table: mesh_message_queue
CREATE TABLE IF NOT EXISTS mesh_message_queue (
    message_id text NOT NULL,
    from_sakhi_id text NOT NULL,
    to_sakhi_id text NOT NULL,
    message_type text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb,
    reply_to text,
    created_at timestamp with time zone DEFAULT now(),
    last_attempt timestamp with time zone,
    attempts integer DEFAULT 0,
    delivered_at timestamp with time zone,
    max_retries integer DEFAULT 5,
    next_retry_at timestamp with time zone,
    status text DEFAULT 'pending'::text,
    error_message text,
    response_received_at timestamp with time zone,
    response_payload jsonb
);

-- Table: mesh_messages
CREATE TABLE IF NOT EXISTS mesh_messages (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    from_sakhi_id uuid NOT NULL,
    to_sakhi_id uuid NOT NULL,
    message_type text NOT NULL,
    payload jsonb NOT NULL,
    conversation_id uuid,
    in_reply_to uuid,
    status text DEFAULT 'sent'::text,
    created_at timestamp with time zone DEFAULT now(),
    delivered_at timestamp with time zone,
    processed_at timestamp with time zone
);

-- Table: mesh_private_keys
CREATE TABLE IF NOT EXISTS mesh_private_keys (
    sakhi_id text NOT NULL,
    encrypted_key text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    rotated_at timestamp with time zone
);

-- Table: mesh_response_correlation
CREATE TABLE IF NOT EXISTS mesh_response_correlation (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    request_message_id text NOT NULL,
    response_message_id text NOT NULL,
    correlated_at timestamp with time zone DEFAULT now()
);

-- Table: meta_reflection_scores
CREATE TABLE IF NOT EXISTS meta_reflection_scores (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    helpfulness numeric,
    clarity numeric,
    tone_feedback text,
    updated_at timestamp without time zone DEFAULT now()
);

-- Table: meta_reflections
CREATE TABLE IF NOT EXISTS meta_reflections (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    period text,
    summary text,
    insights jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: micro_goals
CREATE TABLE IF NOT EXISTS micro_goals (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    source text NOT NULL,
    normalized text NOT NULL,
    micro_steps jsonb NOT NULL,
    confidence double precision NOT NULL DEFAULT 0.7,
    blocked boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: micro_journey_cache
CREATE TABLE IF NOT EXISTS micro_journey_cache (
    person_id uuid NOT NULL,
    journey jsonb NOT NULL,
    flow_count integer NOT NULL,
    rhythm_slot text,
    generated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: micro_momentum_cache
CREATE TABLE IF NOT EXISTS micro_momentum_cache (
    id bigint NOT NULL,
    person_id uuid,
    nudge_date date NOT NULL,
    nudge text DEFAULT ''::text,
    reason text DEFAULT ''::text,
    generated_at timestamp with time zone DEFAULT now()
);

-- Table: micro_recovery_cache
CREATE TABLE IF NOT EXISTS micro_recovery_cache (
    id bigint NOT NULL,
    person_id uuid,
    recovery_date date NOT NULL,
    nudge text DEFAULT ''::text,
    reason text DEFAULT ''::text,
    generated_at timestamp with time zone DEFAULT now()
);

-- Table: mini_flow_cache
CREATE TABLE IF NOT EXISTS mini_flow_cache (
    id bigint NOT NULL,
    person_id uuid,
    flow_date date NOT NULL,
    warmup_step text DEFAULT ''::text,
    focus_block_step text DEFAULT ''::text,
    closure_step text DEFAULT ''::text,
    optional_reward text DEFAULT ''::text,
    source text DEFAULT ''::text,
    generated_at timestamp with time zone DEFAULT now(),
    rhythm_slot text
);

-- Table: mission_checkpoints
CREATE TABLE IF NOT EXISTS mission_checkpoints (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    mission_id uuid NOT NULL,
    checkpoint_date date NOT NULL,
    checkpoint_type text NOT NULL,
    metrics_snapshot jsonb,
    progress_pct integer,
    health text,
    analysis text,
    recommendations text[],
    risks text[],
    adjustments_approved jsonb,
    user_feedback text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: mission_data
CREATE TABLE IF NOT EXISTS mission_data (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    mission_id uuid,
    person_id uuid NOT NULL,
    record_type text NOT NULL,
    data jsonb NOT NULL,
    record_date date,
    source text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: mission_phases
CREATE TABLE IF NOT EXISTS mission_phases (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    mission_id uuid NOT NULL,
    phase_number integer NOT NULL,
    name text NOT NULL,
    objective text,
    start_date date NOT NULL,
    target_end_date date NOT NULL,
    actual_end_date date,
    status text DEFAULT 'pending'::text,
    expected_outcomes jsonb,
    actual_outcomes jsonb,
    requires_approval boolean DEFAULT true,
    approved_at timestamp with time zone,
    approved_by text,
    adjustments_made text[],
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: mission_plan_history
CREATE TABLE IF NOT EXISTS mission_plan_history (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    mission_id uuid NOT NULL,
    plan_document text,
    changed_at timestamp with time zone DEFAULT now(),
    change_summary text,
    changed_by text
);

-- Table: mission_scheduled_actions
CREATE TABLE IF NOT EXISTS mission_scheduled_actions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    mission_id uuid NOT NULL,
    weekly_plan_id uuid,
    person_id uuid NOT NULL,
    action_type text NOT NULL,
    description text NOT NULL,
    instructions jsonb,
    scheduled_date date NOT NULL,
    scheduled_time time without time zone,
    deadline timestamp with time zone,
    trigger_type text DEFAULT 'scheduled'::text,
    cron_expression text,
    trigger_condition text,
    status text DEFAULT 'scheduled'::text,
    agent_session_id uuid,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    outcome jsonb,
    success boolean,
    error_message text,
    effectiveness_score numeric(3,2),
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: mission_weekly_plans
CREATE TABLE IF NOT EXISTS mission_weekly_plans (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    mission_id uuid NOT NULL,
    phase_id uuid,
    week_number integer NOT NULL,
    week_start date NOT NULL,
    week_end date NOT NULL,
    objectives text[],
    tasks jsonb,
    status text DEFAULT 'planned'::text,
    review_completed boolean DEFAULT false,
    review_notes text,
    what_worked text[],
    what_didnt text[],
    adjustments_for_next text[],
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: model_adjustments
CREATE TABLE IF NOT EXISTS model_adjustments (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    pattern_type text NOT NULL,
    delta float8[],
    applied_at timestamp with time zone DEFAULT now(),
    learning_rate double precision DEFAULT 0.1,
    notes text
);

-- Table: morning_ask_cache
CREATE TABLE IF NOT EXISTS morning_ask_cache (
    id bigint NOT NULL,
    person_id uuid,
    ask_date date NOT NULL,
    question text DEFAULT ''::text,
    reason text DEFAULT ''::text,
    generated_at timestamp with time zone DEFAULT now()
);

-- Table: morning_momentum_cache
CREATE TABLE IF NOT EXISTS morning_momentum_cache (
    id bigint NOT NULL,
    person_id uuid,
    momentum_date date NOT NULL,
    momentum_hint text DEFAULT ''::text,
    suggested_start text DEFAULT ''::text,
    reason text DEFAULT ''::text,
    generated_at timestamp with time zone DEFAULT now()
);

-- Table: morning_preview_cache
CREATE TABLE IF NOT EXISTS morning_preview_cache (
    id bigint NOT NULL,
    person_id uuid,
    preview_date date NOT NULL,
    focus_areas jsonb DEFAULT '[]'::jsonb,
    key_tasks jsonb DEFAULT '[]'::jsonb,
    reminders jsonb DEFAULT '[]'::jsonb,
    rhythm_hint text DEFAULT ''::text,
    summary text DEFAULT ''::text,
    generated_at timestamp with time zone DEFAULT now()
);

-- Table: narrative_arc_cache
CREATE TABLE IF NOT EXISTS narrative_arc_cache (
    person_id uuid NOT NULL,
    life_arcs jsonb DEFAULT '{}'::jsonb,
    micro_arcs jsonb DEFAULT '{}'::jsonb,
    active_arcs jsonb DEFAULT '{}'::jsonb,
    arc_states jsonb DEFAULT '{}'::jsonb,
    arc_progress jsonb DEFAULT '{}'::jsonb,
    arc_conflicts jsonb DEFAULT '{}'::jsonb,
    arc_breakthroughs jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: narrative_seasons
CREATE TABLE IF NOT EXISTS narrative_seasons (
    person_id uuid NOT NULL,
    season text NOT NULL,
    hints jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: narrative_stories
CREATE TABLE IF NOT EXISTS narrative_stories (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    narrative text NOT NULL,
    season text,
    patterns_success jsonb NOT NULL DEFAULT '[]'::jsonb,
    patterns_struggle jsonb NOT NULL DEFAULT '[]'::jsonb,
    identity_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: narratives
CREATE TABLE IF NOT EXISTS narratives (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    kind text NOT NULL,
    summary text NOT NULL,
    signals jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: nudge_log
CREATE TABLE IF NOT EXISTS nudge_log (
    id bigint NOT NULL,
    person_id uuid,
    category text NOT NULL,
    message text NOT NULL,
    forecast_snapshot jsonb NOT NULL,
    sent_at timestamp with time zone DEFAULT now()
);

-- Table: parsed_documents
CREATE TABLE IF NOT EXISTS parsed_documents (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    media_id uuid NOT NULL,
    person_id text NOT NULL,
    document_type text,
    title text,
    full_text text,
    pages jsonb DEFAULT '[]'::jsonb,
    extracted_data jsonb DEFAULT '{}'::jsonb,
    search_vector tsvector,
    embedding vector(1536),
    created_at timestamp with time zone DEFAULT now()
);

-- Table: pattern_occurrences
CREATE TABLE IF NOT EXISTS pattern_occurrences (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    pattern_type text NOT NULL,
    pattern_value text NOT NULL,
    episode_id uuid,
    entry_id uuid,
    snippet text,
    confidence double precision DEFAULT 0.5,
    sentiment double precision,
    detected_at timestamp with time zone DEFAULT now()
);

-- Table: pattern_sense_cache
CREATE TABLE IF NOT EXISTS pattern_sense_cache (
    person_id uuid NOT NULL,
    patterns jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: pattern_stats
CREATE TABLE IF NOT EXISTS pattern_stats (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    pattern_type text NOT NULL,
    metric text NOT NULL,
    value double precision,
    confidence double precision,
    window_scope text DEFAULT 'weekly'::text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: person_profile_map
CREATE TABLE IF NOT EXISTS person_profile_map (
    person_id uuid NOT NULL,
    profile_user_id uuid
);

-- Table: persona_evolution
CREATE TABLE IF NOT EXISTS persona_evolution (
    person_id uuid NOT NULL,
    current_mode text,
    drift_score numeric NOT NULL DEFAULT 0.0,
    evolution_path jsonb NOT NULL DEFAULT '[]'::jsonb,
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: persona_modes
CREATE TABLE IF NOT EXISTS persona_modes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    mode_name text,
    activation_score double precision DEFAULT 0.0,
    last_activated timestamp with time zone DEFAULT now()
);

-- Table: persona_traits
CREATE TABLE IF NOT EXISTS persona_traits (
    person_id uuid NOT NULL,
    style_profile jsonb DEFAULT '{}'::jsonb,
    last_updated timestamp with time zone DEFAULT now(),
    sample_conversations integer DEFAULT 0,
    dominant_emotion text,
    tone_bias text,
    expressiveness double precision DEFAULT 0.5,
    humor double precision DEFAULT 0.3,
    reflectiveness double precision DEFAULT 0.7,
    warmth double precision DEFAULT 0.8
);

-- Table: personal_embeddings
CREATE TABLE IF NOT EXISTS personal_embeddings (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    label text,
    content text,
    embedding vector(1536),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: personal_model
CREATE TABLE IF NOT EXISTS personal_model (
    person_id uuid NOT NULL,
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    body_state jsonb DEFAULT '{}'::jsonb,
    mind_state jsonb DEFAULT '{}'::jsonb,
    emotion_state jsonb DEFAULT '{}'::jsonb,
    goals_state jsonb DEFAULT '{}'::jsonb,
    rhythm_state jsonb DEFAULT '{}'::jsonb,
    short_term jsonb DEFAULT '{}'::jsonb,
    long_term jsonb DEFAULT '{}'::jsonb,
    summary_text text,
    last_seen timestamp with time zone DEFAULT now(),
    last_reflection timestamp with time zone,
    coherence numeric DEFAULT 0,
    short_term_vector jsonb DEFAULT '{}'::jsonb,
    emotion text,
    relationship_state jsonb,
    soul_state jsonb DEFAULT '{"longing": [], "aversions": [], "confidence": 0.0, "updated_at": null, "commitments": [], "core_values": [], "light_patterns": [], "identity_themes": [], "shadow_patterns": []}'::jsonb,
    soul_vector vector(1536),
    soul_shadow jsonb DEFAULT '{}'::jsonb,
    soul_light jsonb DEFAULT '{}'::jsonb,
    soul_conflicts jsonb DEFAULT '{}'::jsonb,
    soul_friction jsonb DEFAULT '{}'::jsonb,
    emotion_soul_rhythm_state jsonb DEFAULT '{}'::jsonb,
    identity_momentum_state jsonb DEFAULT '{}'::jsonb,
    internal_decision_graph jsonb DEFAULT '{}'::jsonb,
    identity_timeline jsonb DEFAULT '{}'::jsonb,
    persona_evolution_state jsonb DEFAULT '{}'::jsonb,
    coherence_report jsonb DEFAULT '{}'::jsonb,
    narrative_arcs jsonb DEFAULT '[]'::jsonb,
    pattern_sense jsonb DEFAULT '{}'::jsonb,
    inner_dialogue_state jsonb DEFAULT '{}'::jsonb,
    identity_state jsonb DEFAULT '{}'::jsonb,
    conflict_state jsonb DEFAULT '{}'::jsonb,
    coherence_state jsonb DEFAULT '{}'::jsonb,
    forecast_state jsonb DEFAULT '{}'::jsonb,
    tone_state jsonb DEFAULT '{}'::jsonb,
    nudge_state jsonb DEFAULT '{}'::jsonb,
    empathy_state jsonb DEFAULT '{}'::jsonb,
    daily_reflection_state jsonb DEFAULT '{}'::jsonb,
    closure_state jsonb DEFAULT '{}'::jsonb,
    morning_preview_state jsonb DEFAULT '{}'::jsonb,
    morning_ask_state jsonb DEFAULT '{}'::jsonb,
    morning_momentum_state jsonb DEFAULT '{}'::jsonb,
    micro_momentum_state jsonb DEFAULT '{}'::jsonb,
    micro_recovery_state jsonb DEFAULT '{}'::jsonb,
    focus_path_state jsonb DEFAULT '{}'::jsonb,
    mini_flow_state jsonb DEFAULT '{}'::jsonb,
    mini_flow_rhythm_slot text,
    longitudinal_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    alignment_state jsonb DEFAULT '{}'::jsonb,
    rhythm_soul_state jsonb DEFAULT '{}'::jsonb,
    soul_narrative jsonb DEFAULT '{}'::jsonb,
    operating_system jsonb,
    life_context jsonb,
    decision_profile jsonb
);

-- Table: personal_model_elemental
CREATE TABLE IF NOT EXISTS personal_model_elemental (
    person_id uuid NOT NULL,
    baseline jsonb NOT NULL,
    volatility jsonb NOT NULL,
    recovery_rate jsonb NOT NULL,
    coupling jsonb NOT NULL,
    confidence numeric(4,3) NOT NULL DEFAULT 0.5,
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: personal_model_energy
CREATE TABLE IF NOT EXISTS personal_model_energy (
    person_id uuid NOT NULL,
    baseline jsonb NOT NULL,
    volatility jsonb NOT NULL,
    recovery_profile jsonb NOT NULL,
    circulation_stability jsonb NOT NULL,
    confidence numeric(4,3) NOT NULL DEFAULT 0.5,
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: personal_os_brain
CREATE TABLE IF NOT EXISTS personal_os_brain (
    person_id uuid NOT NULL,
    goals_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    rhythm_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    emotional_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    identity_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    relationship_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    environment_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    habits_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    focus_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    friction_points jsonb NOT NULL DEFAULT '[]'::jsonb,
    top_priorities jsonb NOT NULL DEFAULT '[]'::jsonb,
    life_chapter jsonb NOT NULL DEFAULT '{}'::jsonb,
    working_memory jsonb NOT NULL DEFAULT '{}'::jsonb,
    last_updated timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: personal_patterns
CREATE TABLE IF NOT EXISTS personal_patterns (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    cause_type text NOT NULL,
    cause_value text NOT NULL,
    effect_type text NOT NULL,
    effect_value text NOT NULL,
    correlation_strength double precision NOT NULL DEFAULT 0.5,
    confidence double precision NOT NULL DEFAULT 0.5,
    observation_count integer NOT NULL DEFAULT 1,
    ayurvedic_explanation text,
    related_dosha text,
    first_observed_at timestamp with time zone NOT NULL DEFAULT now(),
    last_observed_at timestamp with time zone NOT NULL DEFAULT now(),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: persons
CREATE TABLE IF NOT EXISTS persons (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: planned_items
CREATE TABLE IF NOT EXISTS planned_items (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    scope text,
    label text,
    payload jsonb,
    due_ts timestamp with time zone,
    recurrence jsonb,
    linked_goal_id uuid,
    goal_id uuid,
    milestone_id uuid,
    status text NOT NULL DEFAULT 'pending'::text,
    priority integer NOT NULL DEFAULT 1,
    energy text,
    ease integer,
    horizon text,
    origin_id text,
    meta jsonb DEFAULT '{}'::jsonb
);

-- Table: planner_context_cache
CREATE TABLE IF NOT EXISTS planner_context_cache (
    person_id uuid NOT NULL,
    payload jsonb NOT NULL,
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: planner_goals
CREATE TABLE IF NOT EXISTS planner_goals (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    title text NOT NULL,
    details text DEFAULT ''::text,
    horizon text NOT NULL DEFAULT 'week'::text,
    priority integer NOT NULL DEFAULT 1,
    status text NOT NULL DEFAULT 'active'::text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: planner_milestones
CREATE TABLE IF NOT EXISTS planner_milestones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    goal_id uuid NOT NULL,
    title text NOT NULL,
    details text DEFAULT ''::text,
    due_ts timestamp with time zone,
    horizon text NOT NULL DEFAULT 'week'::text,
    status text NOT NULL DEFAULT 'active'::text,
    sequence integer NOT NULL DEFAULT 0,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: planner_weekly_pressure
CREATE TABLE IF NOT EXISTS planner_weekly_pressure (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    week_start date NOT NULL,
    week_end date NOT NULL,
    pressure jsonb NOT NULL,
    confidence numeric DEFAULT 0.0,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: preference_adjustments
CREATE TABLE IF NOT EXISTS preference_adjustments (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    domain text NOT NULL,
    dimension text NOT NULL,
    old_value double precision,
    new_value double precision,
    adjustment double precision,
    trigger_type text NOT NULL,
    trigger_id uuid,
    evidence_text text,
    old_confidence double precision,
    new_confidence double precision,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: preference_domains
CREATE TABLE IF NOT EXISTS preference_domains (
    domain_id text NOT NULL,
    display_name text NOT NULL,
    description text,
    standard_dimensions jsonb DEFAULT '[]'::jsonb,
    icon text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: preference_events
CREATE TABLE IF NOT EXISTS preference_events (
    id integer NOT NULL,
    person_id text NOT NULL,
    domain text NOT NULL,
    dimension text NOT NULL,
    value double precision NOT NULL,
    evidence_type text NOT NULL,
    source_text text,
    context jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: preference_match_history
CREATE TABLE IF NOT EXISTS preference_match_history (
    id integer NOT NULL,
    person_id text NOT NULL,
    domain text NOT NULL,
    item_id text,
    item_description text,
    predicted_score double precision,
    actual_feedback double precision,
    feedback_type text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: preference_profiles
CREATE TABLE IF NOT EXISTS preference_profiles (
    person_id text NOT NULL,
    profile_data jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);

-- Table: preference_traits
CREATE TABLE IF NOT EXISTS preference_traits (
    trait_id text NOT NULL,
    display_name text NOT NULL,
    description text,
    related_domains jsonb DEFAULT '[]'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: preferences
CREATE TABLE IF NOT EXISTS preferences (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    scope text,
    key text,
    value jsonb,
    confidence numeric,
    evidence_ids uuid[] DEFAULT '{}'::uuid[]
);

-- Table: presence_state
CREATE TABLE IF NOT EXISTS presence_state (
    person_id uuid NOT NULL,
    date date NOT NULL DEFAULT CURRENT_DATE,
    summary text,
    mood_today text,
    open_actions jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: profiles
CREATE TABLE IF NOT EXISTS profiles (
    user_id uuid NOT NULL,
    email text,
    tz text DEFAULT 'Asia/Kolkata'::text,
    locale text DEFAULT 'en-IN'::text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    allow_bio_data boolean DEFAULT false
);

-- Table: purpose_themes
CREATE TABLE IF NOT EXISTS purpose_themes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    theme text NOT NULL,
    description text,
    anchors jsonb NOT NULL DEFAULT '[]'::jsonb,
    momentum numeric NOT NULL DEFAULT 0.0,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: recommendation_feedback
CREATE TABLE IF NOT EXISTS recommendation_feedback (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    recommendation_type text NOT NULL,
    recommendation_domain text,
    recommendation_content jsonb NOT NULL,
    feedback_type text,
    feedback_text text,
    rating double precision,
    was_followed boolean,
    was_reordered boolean,
    time_to_action_seconds integer,
    affected_dimensions jsonb DEFAULT '[]'::jsonb,
    conversation_id text,
    choice_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    acted_at timestamp with time zone
);

-- Table: reflection_feedback
CREATE TABLE IF NOT EXISTS reflection_feedback (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    reflection_id bigint,
    helpful boolean,
    comment text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: reflection_inquiry_embeddings
CREATE TABLE IF NOT EXISTS reflection_inquiry_embeddings (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    turn_id uuid NOT NULL,
    person_id uuid NOT NULL,
    content_kind text NOT NULL,
    content_text text NOT NULL,
    embedding_vec vector(1536) NOT NULL,
    content_hash text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: reflection_inquiry_turns
CREATE TABLE IF NOT EXISTS reflection_inquiry_turns (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    reflection_id text NOT NULL,
    reflection_kind text,
    question_text text NOT NULL,
    answer_text text NOT NULL,
    answer_mode text NOT NULL,
    sources_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    window_days integer NOT NULL DEFAULT 7
);

-- Table: reflections
CREATE TABLE IF NOT EXISTS reflections (
    id bigint NOT NULL,
    user_id uuid NOT NULL,
    kind text NOT NULL,
    theme text DEFAULT 'general'::text,
    content text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    coherence numeric DEFAULT 0
);

-- Table: registered_agents
CREATE TABLE IF NOT EXISTS registered_agents (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id text NOT NULL,
    agent_name text NOT NULL,
    agent_type text NOT NULL,
    device_id text NOT NULL,
    agent_version text NOT NULL,
    protocol_version text DEFAULT '1.0'::text,
    capabilities jsonb DEFAULT '[]'::jsonb,
    approved_capabilities jsonb DEFAULT '[]'::jsonb,
    platform text NOT NULL,
    platform_version text,
    architecture text,
    auth_token_hash text NOT NULL,
    status text DEFAULT 'registered'::text,
    last_heartbeat_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: relationship_state
CREATE TABLE IF NOT EXISTS relationship_state (
    person_id uuid NOT NULL,
    trust_score numeric DEFAULT 0.4,
    attunement_score numeric DEFAULT 0.4,
    emotional_safety numeric DEFAULT 0.5,
    closeness_stage text DEFAULT 'Warm'::text,
    preference_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
    interaction_patterns jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: relationships
CREATE TABLE IF NOT EXISTS relationships (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    memory_node_id uuid,
    name text NOT NULL,
    relationship_type text NOT NULL,
    closeness double precision DEFAULT 0.5,
    frequency_target text,
    last_seen_at timestamp with time zone,
    last_contact_at timestamp with time zone,
    last_mentioned_at timestamp with time zone,
    their_sakhi_id uuid,
    context jsonb DEFAULT '{}'::jsonb,
    patterns jsonb DEFAULT '{}'::jsonb,
    scheduling jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: rhythm_forecasts
CREATE TABLE IF NOT EXISTS rhythm_forecasts (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    forecast_date date,
    forecast_window text,
    predicted_energy double precision,
    predicted_focus double precision,
    predicted_mood double precision,
    summary text,
    recommendations text[],
    created_at timestamp with time zone DEFAULT now(),
    forecast_text text,
    forecast_vector vector(1536),
    coherence double precision DEFAULT 0,
    predicted_emotion double precision,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: rhythm_insights
CREATE TABLE IF NOT EXISTS rhythm_insights (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    window_start date,
    window_end date,
    pattern_type text,
    summary text,
    recommendation text,
    confidence double precision,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: rhythm_planner_alignment
CREATE TABLE IF NOT EXISTS rhythm_planner_alignment (
    person_id uuid NOT NULL,
    horizon text NOT NULL,
    recommendations jsonb NOT NULL,
    generated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: rhythm_weekly_rollups
CREATE TABLE IF NOT EXISTS rhythm_weekly_rollups (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    week_start date NOT NULL,
    week_end date NOT NULL,
    rollup jsonb NOT NULL,
    confidence numeric DEFAULT 0.0,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: sakhi_connections
CREATE TABLE IF NOT EXISTS sakhi_connections (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    from_entity_id uuid NOT NULL,
    to_entity_id uuid NOT NULL,
    connection_type text NOT NULL DEFAULT 'peer'::text,
    status text NOT NULL DEFAULT 'pending'::text,
    trust_level text DEFAULT 'standard'::text,
    permissions jsonb DEFAULT '{"can_schedule": true, "can_transact": false, "can_auto_book": false, "can_see_prices": true}'::jsonb,
    relationship_id uuid,
    custom_label text,
    notes text,
    first_interaction_at timestamp with time zone,
    last_interaction_at timestamp with time zone,
    interaction_count integer DEFAULT 0,
    connected_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: sakhi_entities
CREATE TABLE IF NOT EXISTS sakhi_entities (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id text NOT NULL,
    entity_type text NOT NULL DEFAULT 'personal'::text,
    display_name text NOT NULL,
    sakhi_handle text,
    bio text,
    business_name text,
    business_type text,
    business_category text[],
    location_name text,
    operating_hours jsonb,
    capabilities jsonb DEFAULT '{"bookings": false, "inquiries": false, "scheduling": true, "transactions": false}'::jsonb,
    share_availability boolean DEFAULT true,
    availability_detail text DEFAULT 'windows'::text,
    auto_accept_from text[] DEFAULT '{}'::text[],
    require_confirmation boolean DEFAULT true,
    auto_respond_inquiries boolean DEFAULT false,
    discoverable boolean DEFAULT true,
    verified boolean DEFAULT false,
    active boolean DEFAULT true,
    last_active_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: sakhi_invite_links
CREATE TABLE IF NOT EXISTS sakhi_invite_links (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL,
    code text NOT NULL,
    custom_message text,
    max_uses integer,
    uses_remaining integer,
    default_trust_level text DEFAULT 'standard'::text,
    expires_at timestamp with time zone,
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: sakhi_offerings
CREATE TABLE IF NOT EXISTS sakhi_offerings (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL,
    offering_type text NOT NULL,
    name text NOT NULL,
    description text,
    category text[],
    tags text[],
    pricing jsonb,
    available boolean DEFAULT true,
    quantity_available integer,
    availability_schedule jsonb,
    requires_booking boolean DEFAULT false,
    duration_minutes integer,
    booking_advance_hours integer,
    images jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: sakhi_registry
CREATE TABLE IF NOT EXISTS sakhi_registry (
    sakhi_id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    display_name text NOT NULL,
    avatar_url text,
    endpoint_url text,
    public_key text,
    mesh_enabled boolean DEFAULT true,
    capabilities jsonb DEFAULT '["scheduling"]'::jsonb,
    discoverable boolean DEFAULT false,
    share_availability boolean DEFAULT true,
    share_preferences boolean DEFAULT false,
    status text DEFAULT 'active'::text,
    last_seen_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: sakhi_reviews
CREATE TABLE IF NOT EXISTS sakhi_reviews (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    reviewer_entity_id uuid NOT NULL,
    reviewed_entity_id uuid NOT NULL,
    transaction_id uuid,
    offering_id uuid,
    thread_id uuid,
    rating double precision NOT NULL,
    title text,
    content text,
    aspect_ratings jsonb,
    response text,
    response_at timestamp with time zone,
    verified_interaction boolean DEFAULT false,
    status text DEFAULT 'published'::text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: sakhi_transactions
CREATE TABLE IF NOT EXISTS sakhi_transactions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    buyer_entity_id uuid NOT NULL,
    seller_entity_id uuid NOT NULL,
    offering_id uuid,
    description text NOT NULL,
    quantity integer DEFAULT 1,
    unit_price numeric(12,2),
    total_amount numeric(12,2),
    currency text DEFAULT 'USD'::text,
    status text NOT NULL DEFAULT 'pending'::text,
    thread_id uuid,
    fulfillment jsonb,
    confirmed_at timestamp with time zone,
    paid_at timestamp with time zone,
    fulfilled_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: salient_memories
CREATE TABLE IF NOT EXISTS salient_memories (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    session_id uuid,
    kind text NOT NULL,
    key text NOT NULL,
    value jsonb NOT NULL,
    source_turn_id uuid,
    salience double precision NOT NULL DEFAULT 0.7,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: scheduling_preferences
CREATE TABLE IF NOT EXISTS scheduling_preferences (
    person_id uuid NOT NULL,
    preferred_times jsonb DEFAULT '{}'::jsonb,
    avoid_times jsonb DEFAULT '{}'::jsonb,
    buffer_minutes integer DEFAULT 30,
    max_events_per_day integer DEFAULT 3,
    preferred_durations jsonb DEFAULT '{}'::jsonb,
    location_preferences jsonb DEFAULT '{}'::jsonb,
    dining_preferences jsonb DEFAULT '{}'::jsonb,
    energy_preferences jsonb DEFAULT '{}'::jsonb,
    communication_preferences jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: scheduling_requests
CREATE TABLE IF NOT EXISTS scheduling_requests (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    original_request text NOT NULL,
    parsed_intent jsonb NOT NULL DEFAULT '{}'::jsonb,
    related_person_ids uuid[] DEFAULT '{}'::uuid[],
    proposed_times jsonb DEFAULT '[]'::jsonb,
    selected_option integer,
    status text NOT NULL DEFAULT 'pending'::text,
    resulting_event_id uuid,
    resolved_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: self_report_body
CREATE TABLE IF NOT EXISTS self_report_body (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    energy_level double precision,
    fatigue_level double precision,
    tension_neck_shoulders double precision,
    tension_back double precision,
    tension_jaw double precision,
    tension_other text,
    hunger_level double precision,
    digestion_quality text,
    bloating boolean,
    elimination_regular boolean,
    feeling_cold boolean,
    feeling_hot boolean,
    hydration_level double precision,
    breath_quality text,
    cravings text[],
    notes text,
    recorded_at timestamp with time zone DEFAULT now()
);

-- Table: sensory_preferences
CREATE TABLE IF NOT EXISTS sensory_preferences (
    person_id uuid NOT NULL,
    temperature jsonb DEFAULT '{}'::jsonb,
    texture jsonb DEFAULT '{}'::jsonb,
    spice jsonb DEFAULT '{}'::jsonb,
    flavor jsonb DEFAULT '{}'::jsonb,
    visual jsonb DEFAULT '{}'::jsonb,
    ambiance jsonb DEFAULT '{}'::jsonb,
    portion jsonb DEFAULT '{}'::jsonb,
    service jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: session_continuity
CREATE TABLE IF NOT EXISTS session_continuity (
    person_id uuid NOT NULL,
    last_emotion text,
    last_interaction_ts timestamp with time zone DEFAULT now(),
    engagement_level numeric DEFAULT 0.5,
    reflection_pending boolean DEFAULT false,
    clarity_level double precision DEFAULT 0
);

-- Table: session_summaries
CREATE TABLE IF NOT EXISTS session_summaries (
    session_id uuid NOT NULL,
    summary text NOT NULL DEFAULT ''::text,
    last_updated timestamp with time zone NOT NULL DEFAULT now(),
    turn_count_at_summary integer DEFAULT 0
);

-- Table: shared_availability
CREATE TABLE IF NOT EXISTS shared_availability (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL,
    availability_type text DEFAULT 'general'::text,
    offering_id uuid,
    valid_from timestamp with time zone NOT NULL,
    valid_until timestamp with time zone NOT NULL,
    busy_free jsonb NOT NULL,
    windows jsonb,
    detailed jsonb,
    computed_at timestamp with time zone DEFAULT now()
);

-- Table: soul_values
CREATE TABLE IF NOT EXISTS soul_values (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    value_name text NOT NULL,
    description text,
    confidence numeric NOT NULL DEFAULT 0.0,
    anchors jsonb NOT NULL DEFAULT '{}'::jsonb,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: surfaced_aspects
CREATE TABLE IF NOT EXISTS surfaced_aspects (
    user_id uuid NOT NULL,
    key text NOT NULL,
    last_surfaced_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: symptom_episodes
CREATE TABLE IF NOT EXISTS symptom_episodes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    symptom text NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    duration_hours integer,
    likely_cause text,
    what_helped jsonb DEFAULT '[]'::jsonb,
    recovery_time_hours integer,
    notes text,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: symptom_log
CREATE TABLE IF NOT EXISTS symptom_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    symptom_type text NOT NULL,
    severity double precision DEFAULT 0.5,
    occurred_at timestamp with time zone DEFAULT now(),
    resolution_time timestamp with time zone,
    interventions_tried jsonb DEFAULT '[]'::jsonb,
    what_helped jsonb DEFAULT '[]'::jsonb,
    what_didnt_help jsonb DEFAULT '[]'::jsonb,
    resolution_summary text,
    related_dosha text,
    created_at timestamp with time zone DEFAULT now(),
    symptom_name text,
    time_of_day text,
    likely_dosha text,
    source text DEFAULT 'inferred'::text,
    related_entry_id text,
    source_text text
);

-- Table: system_events
CREATE TABLE IF NOT EXISTS system_events (
    id bigint NOT NULL,
    ts timestamp with time zone DEFAULT now(),
    person_id uuid,
    layer text,
    event text,
    payload jsonb
);

-- Table: system_tempo
CREATE TABLE IF NOT EXISTS system_tempo (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    phase text,
    tempo double precision,
    coherence double precision,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: task_dependencies
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id uuid NOT NULL,
    depends_on_task_id uuid NOT NULL,
    hard boolean NOT NULL DEFAULT false
);

-- Table: task_routing_cache
CREATE TABLE IF NOT EXISTS task_routing_cache (
    task_id uuid NOT NULL,
    person_id uuid,
    category text NOT NULL,
    recommended_window text,
    reason text,
    forecast_snapshot jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: tasks
CREATE TABLE IF NOT EXISTS tasks (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    title text NOT NULL,
    status text NOT NULL DEFAULT 'todo'::text,
    due_at timestamp with time zone,
    priority integer NOT NULL DEFAULT 0,
    tags text[],
    notes text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    parent_task_id uuid,
    order_index integer NOT NULL DEFAULT 0,
    estimated_min integer,
    value_score integer,
    hard_block boolean NOT NULL DEFAULT false,
    description text DEFAULT ''::text,
    canonical_intent text,
    inferred_time_horizon text,
    energy_cost double precision,
    emotional_fit text,
    auto_priority double precision,
    anchor_goal_id uuid,
    routing_state jsonb DEFAULT '{}'::jsonb
);

-- Table: theme_rhythm_links
CREATE TABLE IF NOT EXISTS theme_rhythm_links (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    theme text NOT NULL,
    correlation double precision,
    clarity_trend double precision,
    energy_trend double precision,
    samples integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: theme_states
CREATE TABLE IF NOT EXISTS theme_states (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    theme text NOT NULL,
    rhythm_state jsonb DEFAULT '{}'::jsonb,
    emotional_state jsonb DEFAULT '{}'::jsonb,
    clarity_score double precision DEFAULT 0.0,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: themes
CREATE TABLE IF NOT EXISTS themes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    name text,
    description text,
    scope text,
    embed vector(1536),
    signals jsonb,
    trend jsonb,
    embed_vec vector(1536)
);

-- Table: thread_continuity_markers
CREATE TABLE IF NOT EXISTS thread_continuity_markers (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    thread_id uuid NOT NULL,
    continuity_hint text,
    persona_stability jsonb NOT NULL DEFAULT '{}'::jsonb,
    last_turn_id uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: user_choices
CREATE TABLE IF NOT EXISTS user_choices (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    choice_context text NOT NULL,
    options_presented jsonb NOT NULL,
    option_count integer DEFAULT 2,
    chosen_option jsonb,
    chosen_index integer,
    inferred_reasons jsonb DEFAULT '[]'::jsonb,
    conversation_id text,
    recommendation_id text,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: users
CREATE TABLE IF NOT EXISTS users (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    email text NOT NULL,
    full_name text,
    password_hash text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Table: vision_memory
CREATE TABLE IF NOT EXISTS vision_memory (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id text NOT NULL,
    media_id uuid,
    memory_type text NOT NULL,
    subject text NOT NULL,
    learned_facts jsonb DEFAULT '[]'::jsonb,
    embedding vector(1536),
    source_description text,
    confidence double precision DEFAULT 0.5,
    first_seen_at timestamp with time zone DEFAULT now(),
    last_confirmed_at timestamp with time zone DEFAULT now(),
    times_seen integer DEFAULT 1,
    created_at timestamp with time zone DEFAULT now()
);

-- Table: visual_context
CREATE TABLE IF NOT EXISTS visual_context (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id text NOT NULL,
    session_id text NOT NULL,
    active_media jsonb DEFAULT '[]'::jsonb,
    visual_summary text,
    objects_mentioned jsonb DEFAULT '[]'::jsonb,
    people_mentioned jsonb DEFAULT '[]'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: wellness_state_cache
CREATE TABLE IF NOT EXISTS wellness_state_cache (
    person_id uuid NOT NULL,
    body jsonb DEFAULT '{}'::jsonb,
    mind jsonb DEFAULT '{}'::jsonb,
    emotion jsonb DEFAULT '{}'::jsonb,
    energy jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

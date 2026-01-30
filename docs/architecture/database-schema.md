# Database Schema

> Auto-generated schema documentation for Sakhi database.
> 
> **Tables:** 117

---

## Table of Contents

### Core
- [users](#users)
- [profiles](#profiles)
- [persons](#persons)
- [auth_users](#auth_users)
- [personal_model](#personal_model)

### Conversation
- [conversation_turns](#conversation_turns)
- [conversation_sessions](#conversation_sessions)
- [conversation_state](#conversation_state)
- [session_summaries](#session_summaries)
- [session_continuity](#session_continuity)

### Memory
- [journal_entries](#journal_entries)
- [journal_embeddings](#journal_embeddings)
- [journal_inference](#journal_inference)
- [memory_short_term](#memory_short_term)
- [memory_episodic](#memory_episodic)
- [memory_context_cache](#memory_context_cache)
- [memory_weekly_signals](#memory_weekly_signals)
- [memory_nodes](#memory_nodes)
- [memory_edges](#memory_edges)

### Patterns
- [pattern_occurrences](#pattern_occurrences)
- [crystallized_patterns](#crystallized_patterns)
- [crystallization_log](#crystallization_log)

### Planning
- [goals](#goals)
- [goal_history](#goal_history)
- [intents](#intents)
- [tasks](#tasks)
- [planned_items](#planned_items)
- [planner_weekly_pressure](#planner_weekly_pressure)

### Rhythm
- [rhythm_weekly_rollups](#rhythm_weekly_rollups)
- [rhythm_forecasts](#rhythm_forecasts)

### Body & Health
- [health_data_sync](#health_data_sync)
- [body_state_history](#body_state_history)
- [self_report_body](#self_report_body)

### Reflection
- [reflections](#reflections)
- [reflection_inquiry_turns](#reflection_inquiry_turns)
- [reflection_inquiry_embeddings](#reflection_inquiry_embeddings)

### Cache Tables
- [daily_reflection_cache](#daily_reflection_cache)
- [morning_preview_cache](#morning_preview_cache)
- [morning_momentum_cache](#morning_momentum_cache)
- [micro_journey_cache](#micro_journey_cache)
- [micro_momentum_cache](#micro_momentum_cache)
- [micro_recovery_cache](#micro_recovery_cache)
- [mini_flow_cache](#mini_flow_cache)
- [focus_path_cache](#focus_path_cache)
- [forecast_cache](#forecast_cache)
- [analytics_cache](#analytics_cache)
- [coherence_cache](#coherence_cache)
- [identity_drift_cache](#identity_drift_cache)

### Ayurvedic
- [elemental_signal_stm](#elemental_signal_stm)

### Other
- [brain_goals_themes](#brain_goals_themes)
- [collective_patterns](#collective_patterns)
- [conversation_suggestions](#conversation_suggestions)
- [daily_alignment_cache](#daily_alignment_cache)
- [daily_closure_cache](#daily_closure_cache)
- [debug_traces](#debug_traces)
- [events](#events)
- [focus_events](#focus_events)
- [focus_sessions](#focus_sessions)
- [growth_daily_checkins](#growth_daily_checkins)
- [growth_habit_logs](#growth_habit_logs)
- [growth_habits](#growth_habits)
- [growth_task_confidence_events](#growth_task_confidence_events)
- [inner_conflict_cache](#inner_conflict_cache)
- [inner_dialogue_cache](#inner_dialogue_cache)
- [insight](#insight)
- [insights_queue](#insights_queue)
- [intent_evolution](#intent_evolution)
- [journal_links](#journal_links)
- [journal_themes](#journal_themes)
- [journey_cache](#journey_cache)
- [memory_monthly_recaps](#memory_monthly_recaps)
- [memory_semantic_rollups](#memory_semantic_rollups)
- [memory_strength_events](#memory_strength_events)
- [memory_theme_drift_events](#memory_theme_drift_events)
- [memory_weekly_summaries](#memory_weekly_summaries)
- [meta_reflection_scores](#meta_reflection_scores)
- [meta_reflections](#meta_reflections)
- [micro_goals](#micro_goals)
- [model_adjustments](#model_adjustments)
- [morning_ask_cache](#morning_ask_cache)
- [narrative_arc_cache](#narrative_arc_cache)
- [narrative_seasons](#narrative_seasons)
- [narrative_stories](#narrative_stories)
- [narratives](#narratives)
- [nudge_log](#nudge_log)
- [pattern_sense_cache](#pattern_sense_cache)
- [pattern_stats](#pattern_stats)
- [person_profile_map](#person_profile_map)
- [persona_evolution](#persona_evolution)
- [persona_modes](#persona_modes)
- [persona_traits](#persona_traits)
- [personal_embeddings](#personal_embeddings)
- [personal_model_elemental](#personal_model_elemental)
- [personal_model_energy](#personal_model_energy)
- [personal_os_brain](#personal_os_brain)
- [planner_context_cache](#planner_context_cache)
- [planner_goals](#planner_goals)
- [planner_milestones](#planner_milestones)
- [preferences](#preferences)
- [presence_state](#presence_state)
- [purpose_themes](#purpose_themes)
- [reflection_feedback](#reflection_feedback)
- [relationship_state](#relationship_state)
- [rhythm_insights](#rhythm_insights)
- [rhythm_planner_alignment](#rhythm_planner_alignment)
- [salient_memories](#salient_memories)
- [soul_values](#soul_values)
- [surfaced_aspects](#surfaced_aspects)
- [system_events](#system_events)
- [system_tempo](#system_tempo)
- [task_dependencies](#task_dependencies)
- [task_routing_cache](#task_routing_cache)
- [theme_rhythm_links](#theme_rhythm_links)
- [theme_states](#theme_states)
- [themes](#themes)
- [thread_continuity_markers](#thread_continuity_markers)
- [wellness_state_cache](#wellness_state_cache)

---

## Core

### users

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `instance_id` | uuid | ✓ |  |
| `id` | uuid |  | gen_random_uuid() |
| `email` | text |  |  |
| `id` | uuid |  |  |
| `aud` | character varying | ✓ |  |
| `full_name` | text | ✓ |  |
| `password_hash` | text | ✓ |  |
| `role` | character varying | ✓ |  |
| `email` | character varying | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |
| `encrypted_password` | character varying | ✓ |  |
| `email_confirmed_at` | timestamp with time zone | ✓ |  |
| `invited_at` | timestamp with time zone | ✓ |  |
| `confirmation_token` | character varying | ✓ |  |
| `confirmation_sent_at` | timestamp with time zone | ✓ |  |
| `recovery_token` | character varying | ✓ |  |
| `recovery_sent_at` | timestamp with time zone | ✓ |  |
| `email_change_token_new` | character varying | ✓ |  |
| `email_change` | character varying | ✓ |  |
| `email_change_sent_at` | timestamp with time zone | ✓ |  |
| `last_sign_in_at` | timestamp with time zone | ✓ |  |
| `raw_app_meta_data` | jsonb | ✓ |  |
| `raw_user_meta_data` | jsonb | ✓ |  |
| `is_super_admin` | boolean | ✓ |  |
| `created_at` | timestamp with time zone | ✓ |  |
| `updated_at` | timestamp with time zone | ✓ |  |
| `phone` | text | ✓ | NULL::character varying |
| `phone_confirmed_at` | timestamp with time zone | ✓ |  |
| `phone_change` | text | ✓ | ''::character varying |
| `phone_change_token` | character varying | ✓ | ''::character varying |
| `phone_change_sent_at` | timestamp with time zone | ✓ |  |
| `confirmed_at` | timestamp with time zone | ✓ |  |
| `email_change_token_current` | character varying | ✓ | ''::character varying |
| `email_change_confirm_status` | smallint | ✓ | 0 |
| `banned_until` | timestamp with time zone | ✓ |  |
| `reauthentication_token` | character varying | ✓ | ''::character varying |
| `reauthentication_sent_at` | timestamp with time zone | ✓ |  |
| `is_sso_user` | boolean |  | false |
| `deleted_at` | timestamp with time zone | ✓ |  |
| `is_anonymous` | boolean |  | false |

### profiles

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `user_id` | uuid |  |  |
| `email` | text | ✓ |  |
| `tz` | text | ✓ | 'Asia/Kolkata'::text |
| `locale` | text | ✓ | 'en-IN'::text |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |
| `allow_bio_data` | boolean | ✓ | false |

### persons

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `created_at` | timestamp with time zone |  | now() |

### auth_users

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `supabase_user_id` | uuid | ✓ |  |
| `email` | text |  |  |
| `full_name` | text | ✓ |  |
| `avatar_url` | text | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |
| `last_sign_in_at` | timestamp with time zone | ✓ |  |
| `onboarding_completed_at` | timestamp with time zone | ✓ |  |
| `deleted_at` | timestamp with time zone | ✓ |  |

### personal_model

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `data` | jsonb |  | '{}'::jsonb |
| `updated_at` | timestamp with time zone |  | now() |
| `body_state` | jsonb | ✓ | '{}'::jsonb |
| `mind_state` | jsonb | ✓ | '{}'::jsonb |
| `emotion_state` | jsonb | ✓ | '{}'::jsonb |
| `goals_state` | jsonb | ✓ | '{}'::jsonb |
| `rhythm_state` | jsonb | ✓ | '{}'::jsonb |
| `short_term` | jsonb | ✓ | '{}'::jsonb |
| `long_term` | jsonb | ✓ | '{}'::jsonb |
| `summary_text` | text | ✓ |  |
| `last_seen` | timestamp with time zone | ✓ | now() |
| `last_reflection` | timestamp with time zone | ✓ |  |
| `coherence` | numeric | ✓ | 0 |
| `short_term_vector` | jsonb | ✓ | '{}'::jsonb |
| `emotion` | text | ✓ |  |
| `relationship_state` | jsonb | ✓ |  |
| `soul_state` | jsonb | ✓ | '{"longing": [], "aversions": [], "co... |
| `soul_vector` | vector | ✓ |  |
| `soul_shadow` | jsonb | ✓ | '{}'::jsonb |
| `soul_light` | jsonb | ✓ | '{}'::jsonb |
| `soul_conflicts` | jsonb | ✓ | '{}'::jsonb |
| `soul_friction` | jsonb | ✓ | '{}'::jsonb |
| `emotion_soul_rhythm_state` | jsonb | ✓ | '{}'::jsonb |
| `identity_momentum_state` | jsonb | ✓ | '{}'::jsonb |
| `internal_decision_graph` | jsonb | ✓ | '{}'::jsonb |
| `identity_timeline` | jsonb | ✓ | '{}'::jsonb |
| `persona_evolution_state` | jsonb | ✓ | '{}'::jsonb |
| `coherence_report` | jsonb | ✓ | '{}'::jsonb |
| `narrative_arcs` | jsonb | ✓ | '[]'::jsonb |
| `pattern_sense` | jsonb | ✓ | '{}'::jsonb |
| `inner_dialogue_state` | jsonb | ✓ | '{}'::jsonb |
| `identity_state` | jsonb | ✓ | '{}'::jsonb |
| `conflict_state` | jsonb | ✓ | '{}'::jsonb |
| `coherence_state` | jsonb | ✓ | '{}'::jsonb |
| `forecast_state` | jsonb | ✓ | '{}'::jsonb |
| `tone_state` | jsonb | ✓ | '{}'::jsonb |
| `nudge_state` | jsonb | ✓ | '{}'::jsonb |
| `empathy_state` | jsonb | ✓ | '{}'::jsonb |
| `daily_reflection_state` | jsonb | ✓ | '{}'::jsonb |
| `closure_state` | jsonb | ✓ | '{}'::jsonb |
| `morning_preview_state` | jsonb | ✓ | '{}'::jsonb |
| `morning_ask_state` | jsonb | ✓ | '{}'::jsonb |
| `morning_momentum_state` | jsonb | ✓ | '{}'::jsonb |
| `micro_momentum_state` | jsonb | ✓ | '{}'::jsonb |
| `micro_recovery_state` | jsonb | ✓ | '{}'::jsonb |
| `focus_path_state` | jsonb | ✓ | '{}'::jsonb |
| `mini_flow_state` | jsonb | ✓ | '{}'::jsonb |
| `mini_flow_rhythm_slot` | text | ✓ |  |
| `longitudinal_state` | jsonb |  | '{}'::jsonb |
| `alignment_state` | jsonb | ✓ | '{}'::jsonb |
| `rhythm_soul_state` | jsonb | ✓ | '{}'::jsonb |
| `soul_narrative` | jsonb | ✓ | '{}'::jsonb |
| `operating_system` | jsonb | ✓ |  |
| `life_context` | jsonb | ✓ |  |
| `decision_profile` | jsonb | ✓ |  |

## Conversation

### conversation_turns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `user_id` | uuid |  |  |
| `session_id` | uuid |  |  |
| `role` | text |  |  |
| `text` | text |  |  |
| `tone` | text | ✓ |  |
| `archetype` | text | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |
| `person_id` | uuid | ✓ |  |
| `reply` | text | ✓ |  |
| `context_version` | integer |  | 1 |
| `queued_jobs` | jsonb |  | '[]'::jsonb |
| `metadata` | jsonb |  | '{}'::jsonb |
| `source` | text | ✓ | 'text'::text |

### conversation_sessions

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `user_id` | uuid |  |  |
| `slug` | text |  |  |
| `title` | text | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |
| `tags` | _text[] | ✓ | '{}'::text[] |
| `status` | text |  | 'active'::text |
| `last_active_at` | timestamp with time zone |  | now() |
| `turn_count` | integer |  | 0 |
| `summary_vec` | vector | ✓ |  |
| `archived_at` | timestamp with time zone | ✓ |  |

### conversation_state

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `last_emotion` | text | ✓ |  |
| `dominant_theme` | text | ✓ |  |
| `last_tone` | text | ✓ |  |
| `clarity_level` | double precision | ✓ |  |
| `energy_level` | double precision | ✓ |  |
| `updated_at` | timestamp with time zone | ✓ | now() |

### session_summaries

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `session_id` | uuid |  |  |
| `summary` | text |  | ''::text |
| `last_updated` | timestamp with time zone |  | now() |

### session_continuity

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `last_emotion` | text | ✓ |  |
| `last_interaction_ts` | timestamp with time zone | ✓ | now() |
| `engagement_level` | numeric | ✓ | 0.5 |
| `reflection_pending` | boolean | ✓ | false |
| `clarity_level` | double precision | ✓ | 0 |

## Memory

### journal_entries

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `user_id` | uuid |  |  |
| `raw_encrypted` | bytea | ✓ |  |
| `cleaned` | text | ✓ |  |
| `facets` | jsonb |  | '{}'::jsonb |
| `salience` | real |  | 0 |
| `ts` | timestamp with time zone |  | now() |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |
| `content` | text | ✓ |  |
| `title` | text | ✓ |  |
| `fts` | tsvector | ✓ |  |
| `raw` | text | ✓ |  |
| `encrypted_preview` | text | ✓ |  |
| `facets_v2` | jsonb | ✓ | '{}'::jsonb |
| `cleaned_tsv` | tsvector | ✓ |  |
| `narrative` | jsonb |  | '{}'::jsonb |
| `debug_payload` | jsonb |  | '{}'::jsonb |
| `layer` | text | ✓ |  |
| `tags` | _text[] | ✓ | '{}'::text[] |
| `source_ref` | jsonb | ✓ | '{}'::jsonb |
| `mood` | text | ✓ |  |
| `person_id` | uuid | ✓ |  |
| `processing_state` | text |  | 'queued'::text |
| `processing_attempts` | integer |  | 0 |
| `processed_at` | timestamp with time zone | ✓ |  |
| `processing_error` | jsonb | ✓ |  |
| `ack_text` | text | ✓ |  |
| `worker_enrichment` | jsonb | ✓ |  |
| `input_type` | text | ✓ |  |
| `client_context` | jsonb | ✓ | '{}'::jsonb |
| `language` | text | ✓ |  |
| `timezone` | text | ✓ |  |
| `user_tags` | _text[] | ✓ | '{}'::text[] |

### journal_embeddings

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `entry_id` | uuid |  |  |
| `model` | text |  | 'text-embedding-3-small'::text |
| `embedding` | vector | ✓ |  |
| `created_at` | timestamp with time zone | ✓ | now() |
| `embedding_vec` | vector | ✓ |  |
| `content_hash` | text | ✓ |  |

### journal_inference

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `entry_id` | uuid |  |  |
| `container` | text |  |  |
| `payload` | jsonb |  | '{}'::jsonb |
| `confidence` | numeric | ✓ |  |
| `inference_type` | text |  |  |
| `source` | text | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |

### memory_short_term

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  |  |
| `user_id` | text |  |  |
| `record` | jsonb |  |  |
| `created_at` | timestamp with time zone |  | now() |
| `soul` | jsonb | ✓ | '{}'::jsonb |
| `soul_shadow` | jsonb | ✓ | '{}'::jsonb |
| `soul_light` | jsonb | ✓ | '{}'::jsonb |
| `content_hash` | text | ✓ |  |
| `vector_vec` | vector | ✓ |  |
| `expires_at` | timestamp with time zone |  | (now() + ((COALESCE((NULLIF(current_s... |
| `entry_id` | uuid | ✓ |  |
| `text` | text | ✓ |  |
| `layer` | text | ✓ |  |
| `triage` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |
| `person_id` | text | ✓ |  |

### memory_episodic

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  |  |
| `user_id` | text |  |  |
| `record` | jsonb |  |  |
| `created_at` | timestamp with time zone |  | now() |
| `soul` | jsonb | ✓ | '{}'::jsonb |
| `soul_shadow` | jsonb | ✓ | '{}'::jsonb |
| `soul_light` | jsonb | ✓ | '{}'::jsonb |
| `soul_conflict` | jsonb | ✓ | '{}'::jsonb |
| `soul_friction` | jsonb | ✓ | '{}'::jsonb |
| `emotion_loop` | jsonb | ✓ | '{}'::jsonb |
| `content_hash` | text | ✓ |  |
| `vector_vec` | vector | ✓ |  |
| `context_tags` | jsonb | ✓ | '[]'::jsonb |
| `entry_id` | uuid | ✓ |  |
| `person_id` | uuid | ✓ |  |
| `triage` | jsonb | ✓ |  |
| `time_scope` | timestamp with time zone | ✓ |  |
| `updated_at` | timestamp with time zone | ✓ | now() |
| `text` | text | ✓ |  |
| `rhythm_state` | jsonb | ✓ | '{}'::jsonb |
| `emotional_state` | jsonb | ✓ | '{}'::jsonb |
| `ts` | timestamp with time zone | ✓ | now() |
| `state_vector` | jsonb | ✓ |  |
| `guna_vector` | jsonb | ✓ |  |

### memory_context_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `window_kind` | text |  | 'default'::text |
| `entries` | jsonb |  | '[]'::jsonb |
| `rhythm_state` | jsonb |  | '{}'::jsonb |
| `persona_snapshot` | jsonb |  | '{}'::jsonb |
| `task_window` | jsonb |  | '[]'::jsonb |
| `version` | integer |  | 1 |
| `updated_at` | timestamp with time zone |  | now() |
| `merged_context_vector` | vector | ✓ |  |

### memory_weekly_signals

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `week_start` | date |  |  |
| `week_end` | date |  |  |
| `episodic_stats` | jsonb |  | '{}'::jsonb |
| `theme_stats` | jsonb |  | '[]'::jsonb |
| `contrast_stats` | jsonb |  | '{}'::jsonb |
| `delta_stats` | jsonb |  | '{}'::jsonb |
| `confidence` | numeric |  | 0.0 |
| `created_at` | timestamp with time zone |  | now() |
| `weekly_contrast` | jsonb | ✓ | '{"count": 0, "positive_glimpses": []... |
| `dimension_states` | jsonb | ✓ | '{"body": "flat", "mind": "flat", "wo... |
| `weekly_salience` | jsonb | ✓ | '{"items": [], "present": false}'::jsonb |
| `weekly_body_notes` | jsonb | ✓ | '{"count": 0, "discomfort_hints": []}... |

### memory_nodes

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `node_kind` | text | ✓ |  |
| `label` | text | ✓ |  |
| `data` | jsonb | ✓ | '{}'::jsonb |
| `created_at` | timestamp with time zone | ✓ | now() |
| `weight` | double precision | ✓ | 0.5 |
| `updated_at` | timestamp with time zone | ✓ | now() |
| `last_referenced_at` | timestamp with time zone | ✓ | now() |

### memory_edges

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `from_node` | uuid | ✓ |  |
| `to_node` | uuid | ✓ |  |
| `relation` | text | ✓ |  |
| `weight` | double precision | ✓ | 0.5 |
| `updated_at` | timestamp with time zone | ✓ | now() |
| `relevance` | double precision | ✓ | 0.5 |
| `created_at` | timestamp with time zone | ✓ | now() |
| `evidence` | jsonb | ✓ | '{}'::jsonb |
| `occurrence_count` | integer | ✓ | 1 |

## Patterns

### pattern_occurrences

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `pattern_type` | text |  |  |
| `pattern_value` | text |  |  |
| `episode_id` | uuid | ✓ |  |
| `entry_id` | uuid | ✓ |  |
| `snippet` | text | ✓ |  |
| `confidence` | double precision | ✓ | 0.5 |
| `sentiment` | double precision | ✓ |  |
| `detected_at` | timestamp with time zone | ✓ | now() |

### crystallized_patterns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `pattern_type` | text |  |  |
| `pattern_value` | text |  |  |
| `sub_topic` | text | ✓ |  |
| `summary` | text | ✓ |  |
| `constitution_relevance` | text | ✓ |  |
| `evidence_ids` | _uuid[] | ✓ | '{}'::uuid[] |
| `evidence_snippets` | jsonb | ✓ | '[]'::jsonb |
| `mention_count` | integer |  | 0 |
| `distinct_days` | integer |  | 0 |
| `confidence` | double precision |  | 0.0 |
| `threshold_met_at` | timestamp with time zone | ✓ |  |
| `trajectory` | text | ✓ | 'stable'::text |
| `trajectory_data` | jsonb | ✓ | '{}'::jsonb |
| `status` | text |  | 'emerging'::text |
| `first_seen` | timestamp with time zone |  | now() |
| `last_seen` | timestamp with time zone |  | now() |
| `crystallized_at` | timestamp with time zone | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |

### crystallization_log

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `crystallized_pattern_id` | uuid | ✓ |  |
| `pattern_type` | text |  |  |
| `pattern_value` | text |  |  |
| `occurrence_count` | integer | ✓ |  |
| `distinct_days` | integer | ✓ |  |
| `confidence` | double precision | ✓ |  |
| `span_days` | integer | ✓ |  |
| `threshold_config` | jsonb | ✓ |  |
| `evidence_ids` | _uuid[] | ✓ |  |
| `action` | text | ✓ |  |
| `crystallized_at` | timestamp with time zone | ✓ | now() |

## Planning

### goals

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `parent_goal_id` | uuid | ✓ |  |
| `title` | text | ✓ |  |
| `description` | text | ✓ |  |
| `horizon` | text | ✓ |  |
| `status` | text | ✓ |  |
| `progress` | numeric | ✓ | 0 |
| `evolution_score` | double precision | ✓ | 0.0 |
| `last_revised` | timestamp with time zone | ✓ | now() |
| `updated_at` | timestamp with time zone |  | now() |
| `type` | text | ✓ | 'goal'::text |
| `priority` | integer | ✓ | 0 |
| `due_at` | timestamp with time zone | ✓ |  |
| `meta` | jsonb | ✓ | '{}'::jsonb |
| `created_at` | timestamp with time zone | ✓ | now() |
| `completed_at` | timestamp with time zone | ✓ |  |

### goal_history

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `goal_id` | uuid | ✓ |  |
| `person_id` | uuid | ✓ |  |
| `previous_title` | text | ✓ |  |
| `previous_description` | text | ✓ |  |
| `revised_title` | text | ✓ |  |
| `revised_description` | text | ✓ |  |
| `reason` | text | ✓ |  |
| `created_at` | timestamp with time zone | ✓ | now() |

### intents

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('intents_id_seq'::regclass) |
| `user_id` | uuid |  |  |
| `source_entry_id` | uuid | ✓ |  |
| `title` | text |  |  |
| `raw_input` | text | ✓ |  |
| `intent_type` | text |  |  |
| `domain` | text | ✓ |  |
| `timeline` | text |  | 'none'::text |
| `target_date` | date | ✓ |  |
| `priority` | smallint | ✓ |  |
| `status` | text |  | 'draft'::text |
| `clarity_score` | numeric | ✓ | 0.0 |
| `user_permission` | boolean | ✓ | false |
| `proposed_plan` | jsonb | ✓ |  |
| `context_snapshot` | jsonb | ✓ | '{}'::jsonb |
| `created_at` | timestamp with time zone | ✓ | now() |
| `updated_at` | timestamp with time zone | ✓ | now() |

### tasks

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `user_id` | uuid |  |  |
| `title` | text |  |  |
| `status` | text |  | 'todo'::text |
| `due_at` | timestamp with time zone | ✓ |  |
| `priority` | integer |  | 0 |
| `tags` | _text[] | ✓ |  |
| `notes` | text | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |
| `parent_task_id` | uuid | ✓ |  |
| `order_index` | integer |  | 0 |
| `estimated_min` | integer | ✓ |  |
| `value_score` | integer | ✓ |  |
| `hard_block` | boolean |  | false |
| `description` | text | ✓ | ''::text |
| `canonical_intent` | text | ✓ |  |
| `inferred_time_horizon` | text | ✓ |  |
| `energy_cost` | double precision | ✓ |  |
| `emotional_fit` | text | ✓ |  |
| `auto_priority` | double precision | ✓ |  |
| `anchor_goal_id` | uuid | ✓ |  |
| `routing_state` | jsonb | ✓ | '{}'::jsonb |

### planned_items

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `scope` | text | ✓ |  |
| `label` | text | ✓ |  |
| `payload` | jsonb | ✓ |  |
| `due_ts` | timestamp with time zone | ✓ |  |
| `recurrence` | jsonb | ✓ |  |
| `linked_goal_id` | uuid | ✓ |  |
| `goal_id` | uuid | ✓ |  |
| `milestone_id` | uuid | ✓ |  |
| `status` | text |  | 'pending'::text |
| `priority` | integer |  | 1 |
| `energy` | text | ✓ |  |
| `ease` | integer | ✓ |  |
| `horizon` | text | ✓ |  |
| `origin_id` | text | ✓ |  |
| `meta` | jsonb | ✓ | '{}'::jsonb |

### planner_weekly_pressure

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `week_start` | date |  |  |
| `week_end` | date |  |  |
| `pressure` | jsonb |  |  |
| `confidence` | numeric | ✓ | 0.0 |
| `created_at` | timestamp with time zone | ✓ | now() |

## Rhythm

### rhythm_weekly_rollups

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `week_start` | date |  |  |
| `week_end` | date |  |  |
| `rollup` | jsonb |  |  |
| `confidence` | numeric | ✓ | 0.0 |
| `created_at` | timestamp with time zone | ✓ | now() |

### rhythm_forecasts

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `forecast_date` | date | ✓ |  |
| `forecast_window` | text | ✓ |  |
| `predicted_energy` | double precision | ✓ |  |
| `predicted_focus` | double precision | ✓ |  |
| `predicted_mood` | double precision | ✓ |  |
| `summary` | text | ✓ |  |
| `recommendations` | _text[] | ✓ |  |
| `created_at` | timestamp with time zone | ✓ | now() |
| `forecast_text` | text | ✓ |  |
| `forecast_vector` | vector | ✓ |  |
| `coherence` | double precision | ✓ | 0 |
| `predicted_emotion` | double precision | ✓ |  |
| `updated_at` | timestamp with time zone | ✓ | now() |

## Body & Health

### health_data_sync

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `source` | text |  |  |
| `data_type` | text |  |  |
| `data` | jsonb |  |  |
| `recorded_at` | timestamp with time zone |  |  |
| `synced_at` | timestamp with time zone | ✓ | now() |
| `processed` | boolean | ✓ | false |
| `processed_at` | timestamp with time zone | ✓ |  |

### body_state_history

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `body_state` | jsonb |  |  |
| `computed_at` | timestamp with time zone | ✓ | now() |
| `overall_score` | double precision | ✓ |  |
| `vata_score` | double precision | ✓ |  |
| `pitta_score` | double precision | ✓ |  |
| `kapha_score` | double precision | ✓ |  |
| `ojas_level` | double precision | ✓ |  |
| `sleep_quality` | double precision | ✓ |  |
| `energy_level` | double precision | ✓ |  |

### self_report_body

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `energy_level` | double precision | ✓ |  |
| `fatigue_level` | double precision | ✓ |  |
| `tension_neck_shoulders` | double precision | ✓ |  |
| `tension_back` | double precision | ✓ |  |
| `tension_jaw` | double precision | ✓ |  |
| `tension_other` | text | ✓ |  |
| `hunger_level` | double precision | ✓ |  |
| `digestion_quality` | text | ✓ |  |
| `bloating` | boolean | ✓ |  |
| `elimination_regular` | boolean | ✓ |  |
| `feeling_cold` | boolean | ✓ |  |
| `feeling_hot` | boolean | ✓ |  |
| `hydration_level` | double precision | ✓ |  |
| `breath_quality` | text | ✓ |  |
| `cravings` | _text[] | ✓ |  |
| `notes` | text | ✓ |  |
| `recorded_at` | timestamp with time zone | ✓ | now() |

## Reflection

### reflections

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('reflections_id_seq'::regclass) |
| `user_id` | uuid |  |  |
| `kind` | text |  |  |
| `theme` | text | ✓ | 'general'::text |
| `content` | text |  |  |
| `created_at` | timestamp with time zone |  | now() |
| `coherence` | numeric | ✓ | 0 |

### reflection_inquiry_turns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `reflection_id` | text |  |  |
| `reflection_kind` | text | ✓ |  |
| `question_text` | text |  |  |
| `answer_text` | text |  |  |
| `answer_mode` | text |  |  |
| `sources_json` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |
| `window_days` | integer |  | 7 |

### reflection_inquiry_embeddings

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `turn_id` | uuid |  |  |
| `person_id` | uuid |  |  |
| `content_kind` | text |  |  |
| `content_text` | text |  |  |
| `embedding_vec` | vector |  |  |
| `content_hash` | text |  |  |
| `created_at` | timestamp with time zone |  | now() |

## Cache Tables

### daily_reflection_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `reflection_date` | date |  |  |
| `summary` | jsonb |  |  |
| `generated_at` | timestamp with time zone | ✓ | now() |

### morning_preview_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('morning_preview_cache_id_seq... |
| `person_id` | uuid | ✓ |  |
| `preview_date` | date |  |  |
| `focus_areas` | jsonb | ✓ | '[]'::jsonb |
| `key_tasks` | jsonb | ✓ | '[]'::jsonb |
| `reminders` | jsonb | ✓ | '[]'::jsonb |
| `rhythm_hint` | text | ✓ | ''::text |
| `summary` | text | ✓ | ''::text |
| `generated_at` | timestamp with time zone | ✓ | now() |

### morning_momentum_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('morning_momentum_cache_id_se... |
| `person_id` | uuid | ✓ |  |
| `momentum_date` | date |  |  |
| `momentum_hint` | text | ✓ | ''::text |
| `suggested_start` | text | ✓ | ''::text |
| `reason` | text | ✓ | ''::text |
| `generated_at` | timestamp with time zone | ✓ | now() |

### micro_journey_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `journey` | jsonb |  |  |
| `flow_count` | integer |  |  |
| `rhythm_slot` | text | ✓ |  |
| `generated_at` | timestamp with time zone |  | now() |

### micro_momentum_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('micro_momentum_cache_id_seq'... |
| `person_id` | uuid | ✓ |  |
| `nudge_date` | date |  |  |
| `nudge` | text | ✓ | ''::text |
| `reason` | text | ✓ | ''::text |
| `generated_at` | timestamp with time zone | ✓ | now() |

### micro_recovery_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('micro_recovery_cache_id_seq'... |
| `person_id` | uuid | ✓ |  |
| `recovery_date` | date |  |  |
| `nudge` | text | ✓ | ''::text |
| `reason` | text | ✓ | ''::text |
| `generated_at` | timestamp with time zone | ✓ | now() |

### mini_flow_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('mini_flow_cache_id_seq'::reg... |
| `person_id` | uuid | ✓ |  |
| `flow_date` | date |  |  |
| `warmup_step` | text | ✓ | ''::text |
| `focus_block_step` | text | ✓ | ''::text |
| `closure_step` | text | ✓ | ''::text |
| `optional_reward` | text | ✓ | ''::text |
| `source` | text | ✓ | ''::text |
| `generated_at` | timestamp with time zone | ✓ | now() |
| `rhythm_slot` | text | ✓ |  |

### focus_path_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('focus_path_cache_id_seq'::re... |
| `person_id` | uuid | ✓ |  |
| `path_date` | date |  |  |
| `anchor_step` | text | ✓ | ''::text |
| `progress_step` | text | ✓ | ''::text |
| `closure_step` | text | ✓ | ''::text |
| `intent_source` | text | ✓ | ''::text |
| `generated_at` | timestamp with time zone | ✓ | now() |

### forecast_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `forecast_state` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |

### analytics_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `metric` | text |  |  |
| `value` | double precision | ✓ |  |
| `period` | text | ✓ | 'weekly'::text |
| `computed_at` | timestamp with time zone | ✓ | now() |

### coherence_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `coherence_state` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |

### identity_drift_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `identity_state` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |

## Ayurvedic

### elemental_signal_stm

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `source_signal_id` | uuid |  |  |
| `source_type` | text |  |  |
| `dimension` | text |  |  |
| `earth` | numeric |  | 0 |
| `water` | numeric |  | 0 |
| `fire` | numeric |  | 0 |
| `air` | numeric |  | 0 |
| `ether` | numeric |  | 0 |
| `confidence` | numeric |  | 1.0 |
| `created_at` | timestamp with time zone |  | now() |
| `expires_at` | timestamp with time zone |  |  |
| `magnitude` | numeric |  | 0 |

## Other Tables

### brain_goals_themes

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `cluster_title` | text | ✓ |  |
| `cluster_vector` | vector | ✓ |  |
| `supporting_entry_ids` | _uuid[] | ✓ |  |
| `confidence` | double precision | ✓ |  |
| `time_window` | text | ✓ |  |
| `emotional_tone` | jsonb | ✓ |  |
| `value_mapping` | jsonb | ✓ |  |
| `identity_alignment` | double precision | ✓ |  |
| `created_at` | timestamp with time zone | ✓ | now() |
| `updated_at` | timestamp with time zone | ✓ | now() |

### collective_patterns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `pattern_type` | text |  |  |
| `mean_vector` | vector | ✓ |  |
| `std_dev_vector` | vector | ✓ |  |
| `support_count` | integer |  | 0 |
| `last_updated` | timestamp with time zone | ✓ | now() |
| `metadata` | jsonb | ✓ | '{}'::jsonb |

### conversation_suggestions

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `suggestion` | text |  |  |
| `style` | text | ✓ |  |
| `confidence` | double precision | ✓ |  |
| `payload` | jsonb | ✓ | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### daily_alignment_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `alignment_map` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |

### daily_closure_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('daily_closure_cache_id_seq':... |
| `person_id` | uuid | ✓ |  |
| `closure_date` | date |  |  |
| `completed` | jsonb | ✓ | '[]'::jsonb |
| `pending` | jsonb | ✓ | '[]'::jsonb |
| `signals` | jsonb | ✓ | '{}'::jsonb |
| `summary` | text | ✓ | ''::text |
| `generated_at` | timestamp with time zone | ✓ | now() |

### debug_traces

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `trace_id` | text |  |  |
| `created_at` | timestamp with time zone |  | now() |
| `flow` | text |  |  |
| `payload` | jsonb |  |  |
| `human_narrative` | text | ✓ |  |
| `plain_layers` | jsonb | ✓ |  |
| `finished_at` | timestamp with time zone | ✓ | now() |
| `success` | boolean | ✓ | false |
| `summary` | jsonb | ✓ | '{}'::jsonb |

### events

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `user_id` | uuid |  |  |
| `type` | text |  |  |
| `v` | integer |  | 1 |
| `ts` | timestamp with time zone |  | now() |
| `idempotency_key` | text | ✓ |  |
| `payload` | jsonb |  |  |
| `occurred_at` | timestamp with time zone |  | now() |
| `event_type` | text |  |  |
| `response` | jsonb | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |

### focus_events

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `session_id` | uuid |  |  |
| `ts` | timestamp with time zone |  | now() |
| `event_type` | text |  |  |
| `content` | jsonb |  | '{}'::jsonb |
| `rhythm_state` | jsonb |  | '{}'::jsonb |
| `task_state` | jsonb |  | '{}'::jsonb |
| `emotion_state` | jsonb |  | '{}'::jsonb |

### focus_sessions

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `task_id` | uuid | ✓ |  |
| `mode` | text | ✓ | 'deep'::text |
| `start_time` | timestamp with time zone |  | now() |
| `end_time` | timestamp with time zone | ✓ |  |
| `estimated_duration` | integer | ✓ |  |
| `actual_duration` | integer | ✓ |  |
| `completion_score` | numeric | ✓ |  |
| `session_quality` | jsonb |  | '{}'::jsonb |
| `session_start_state` | jsonb |  | '{}'::jsonb |
| `status` | text |  | 'active'::text |
| `created_at` | timestamp with time zone |  | now() |

### growth_daily_checkins

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `checkin_date` | date |  | CURRENT_DATE |
| `energy` | numeric | ✓ |  |
| `mood` | text | ✓ |  |
| `reflection` | text | ✓ |  |
| `plan_adjustment` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### growth_habit_logs

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `habit_id` | uuid |  |  |
| `person_id` | uuid |  |  |
| `logged_at` | timestamp with time zone |  | now() |
| `micro_score` | numeric |  | 0.2 |
| `mood` | text | ✓ |  |
| `note` | text | ✓ |  |
| `payload` | jsonb |  | '{}'::jsonb |

### growth_habits

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `label` | text |  |  |
| `cadence` | jsonb |  | '{}'::jsonb |
| `intent_source` | text | ✓ |  |
| `streak_count` | integer |  | 0 |
| `micro_progress` | numeric |  | 0.0 |
| `confidence` | numeric |  | 0.5 |
| `last_logged` | timestamp with time zone | ✓ |  |
| `active` | boolean |  | true |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |

### growth_task_confidence_events

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `task_id` | uuid | ✓ |  |
| `task_label` | text | ✓ |  |
| `confidence_before` | numeric | ✓ |  |
| `confidence_after` | numeric | ✓ |  |
| `delta` | numeric | ✓ |  |
| `source` | text | ✓ |  |
| `payload` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### inner_conflict_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `conflict_state` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |

### inner_dialogue_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `dialogue` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |

### insight

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | text |  |  |
| `person_id` | uuid |  |  |
| `from_ids` | _text[] |  |  |
| `kind` | text |  |  |
| `message` | text |  |  |
| `why` | jsonb | ✓ |  |
| `actions` | jsonb | ✓ |  |
| `confidence` | numeric | ✓ | 0.6 |
| `ts` | timestamp with time zone |  | now() |

### insights_queue

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `insight` | jsonb |  |  |
| `priority` | text | ✓ | 'medium'::text |
| `timing_hint` | text | ✓ | 'next_check_in'::text |
| `delivered` | boolean | ✓ | false |
| `created_at` | timestamp with time zone | ✓ | now() |

### intent_evolution

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `intent_name` | text |  |  |
| `strength` | double precision | ✓ | 0 |
| `emotional_alignment` | double precision | ✓ | 0 |
| `trend` | text | ✓ | 'stable'::text |
| `last_seen` | timestamp with time zone | ✓ | now() |
| `first_seen` | timestamp with time zone | ✓ | now() |

### journal_links

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `src_id` | uuid |  |  |
| `dst_id` | uuid |  |  |
| `strength` | numeric |  |  |
| `created_at` | timestamp with time zone | ✓ | now() |

### journal_themes

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('journal_themes_id_seq'::regc... |
| `user_id` | uuid |  |  |
| `theme` | text |  |  |
| `time_window` | text |  |  |
| `metrics` | jsonb |  |  |
| `created_at` | timestamp with time zone | ✓ | now() |
| `description` | text | ✓ |  |
| `domain` | text | ✓ |  |
| `examples` | jsonb | ✓ |  |

### journey_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `scope` | text |  |  |
| `payload` | jsonb |  | '{}'::jsonb |
| `updated_at` | timestamp with time zone |  | now() |

### memory_monthly_recaps

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `month_scope` | daterange |  |  |
| `summary` | jsonb |  | '{}'::jsonb |
| `highlights` | text | ✓ |  |
| `top_themes` | jsonb |  | '[]'::jsonb |
| `chapter_hint` | text | ✓ |  |
| `drift_score` | numeric |  | 0.0 |
| `compression` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### memory_semantic_rollups

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `source_id` | uuid |  |  |
| `source_kind` | text |  |  |
| `semantic_summary` | text |  |  |
| `strength` | numeric |  | 0.0 |
| `payload` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### memory_strength_events

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `event_kind` | text |  |  |
| `target` | text |  |  |
| `weight` | numeric |  | 0.0 |
| `payload` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### memory_theme_drift_events

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `horizon` | text |  |  |
| `from_theme` | text | ✓ |  |
| `to_theme` | text | ✓ |  |
| `drift_score` | numeric |  | 0.0 |
| `evidence` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### memory_weekly_summaries

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `week_start` | date |  |  |
| `week_end` | date |  |  |
| `summary` | jsonb |  | '{}'::jsonb |
| `highlights` | text | ✓ |  |
| `top_themes` | jsonb |  | '[]'::jsonb |
| `drift_score` | numeric |  | 0.0 |
| `semantic_notes` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### meta_reflection_scores

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `helpfulness` | numeric | ✓ |  |
| `clarity` | numeric | ✓ |  |
| `tone_feedback` | text | ✓ |  |
| `updated_at` | timestamp without time zone | ✓ | now() |

### meta_reflections

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `period` | text | ✓ |  |
| `summary` | text | ✓ |  |
| `insights` | jsonb | ✓ | '{}'::jsonb |
| `created_at` | timestamp with time zone | ✓ | now() |

### micro_goals

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `source` | text |  |  |
| `normalized` | text |  |  |
| `micro_steps` | jsonb |  |  |
| `confidence` | double precision |  | 0.7 |
| `blocked` | boolean |  | false |
| `created_at` | timestamp with time zone | ✓ | now() |
| `updated_at` | timestamp with time zone | ✓ | now() |

### model_adjustments

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `pattern_type` | text |  |  |
| `delta` | _float8[] | ✓ |  |
| `applied_at` | timestamp with time zone | ✓ | now() |
| `learning_rate` | double precision | ✓ | 0.1 |
| `notes` | text | ✓ |  |

### morning_ask_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('morning_ask_cache_id_seq'::r... |
| `person_id` | uuid | ✓ |  |
| `ask_date` | date |  |  |
| `question` | text | ✓ | ''::text |
| `reason` | text | ✓ | ''::text |
| `generated_at` | timestamp with time zone | ✓ | now() |

### narrative_arc_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `life_arcs` | jsonb | ✓ | '{}'::jsonb |
| `micro_arcs` | jsonb | ✓ | '{}'::jsonb |
| `active_arcs` | jsonb | ✓ | '{}'::jsonb |
| `arc_states` | jsonb | ✓ | '{}'::jsonb |
| `arc_progress` | jsonb | ✓ | '{}'::jsonb |
| `arc_conflicts` | jsonb | ✓ | '{}'::jsonb |
| `arc_breakthroughs` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |

### narrative_seasons

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `season` | text |  |  |
| `hints` | jsonb |  | '{}'::jsonb |
| `updated_at` | timestamp with time zone |  | now() |

### narrative_stories

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `narrative` | text |  |  |
| `season` | text | ✓ |  |
| `patterns_success` | jsonb |  | '[]'::jsonb |
| `patterns_struggle` | jsonb |  | '[]'::jsonb |
| `identity_snapshot` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### narratives

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `kind` | text |  |  |
| `summary` | text |  |  |
| `signals` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### nudge_log

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('nudge_log_id_seq'::regclass) |
| `person_id` | uuid | ✓ |  |
| `category` | text |  |  |
| `message` | text |  |  |
| `forecast_snapshot` | jsonb |  |  |
| `sent_at` | timestamp with time zone | ✓ | now() |

### pattern_sense_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `patterns` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |

### pattern_stats

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `pattern_type` | text |  |  |
| `metric` | text |  |  |
| `value` | double precision | ✓ |  |
| `confidence` | double precision | ✓ |  |
| `window_scope` | text | ✓ | 'weekly'::text |
| `created_at` | timestamp with time zone | ✓ | now() |

### person_profile_map

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `profile_user_id` | uuid | ✓ |  |

### persona_evolution

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `current_mode` | text | ✓ |  |
| `drift_score` | numeric |  | 0.0 |
| `evolution_path` | jsonb |  | '[]'::jsonb |
| `updated_at` | timestamp with time zone |  | now() |

### persona_modes

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `mode_name` | text | ✓ |  |
| `activation_score` | double precision | ✓ | 0.0 |
| `last_activated` | timestamp with time zone | ✓ | now() |

### persona_traits

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `style_profile` | jsonb | ✓ | '{}'::jsonb |
| `last_updated` | timestamp with time zone | ✓ | now() |
| `sample_conversations` | integer | ✓ | 0 |
| `dominant_emotion` | text | ✓ |  |
| `tone_bias` | text | ✓ |  |
| `expressiveness` | double precision | ✓ | 0.5 |
| `humor` | double precision | ✓ | 0.3 |
| `reflectiveness` | double precision | ✓ | 0.7 |
| `warmth` | double precision | ✓ | 0.8 |

### personal_embeddings

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `label` | text | ✓ |  |
| `content` | text | ✓ |  |
| `embedding` | vector | ✓ |  |
| `updated_at` | timestamp with time zone | ✓ | now() |

### personal_model_elemental

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `baseline` | jsonb |  |  |
| `volatility` | jsonb |  |  |
| `recovery_rate` | jsonb |  |  |
| `coupling` | jsonb |  |  |
| `confidence` | numeric |  | 0.5 |
| `updated_at` | timestamp with time zone |  | now() |

### personal_model_energy

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `baseline` | jsonb |  |  |
| `volatility` | jsonb |  |  |
| `recovery_profile` | jsonb |  |  |
| `circulation_stability` | jsonb |  |  |
| `confidence` | numeric |  | 0.5 |
| `updated_at` | timestamp with time zone |  | now() |

### personal_os_brain

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `goals_state` | jsonb |  | '{}'::jsonb |
| `rhythm_state` | jsonb |  | '{}'::jsonb |
| `emotional_state` | jsonb |  | '{}'::jsonb |
| `identity_state` | jsonb |  | '{}'::jsonb |
| `relationship_state` | jsonb |  | '{}'::jsonb |
| `environment_state` | jsonb |  | '{}'::jsonb |
| `habits_state` | jsonb |  | '{}'::jsonb |
| `focus_state` | jsonb |  | '{}'::jsonb |
| `friction_points` | jsonb |  | '[]'::jsonb |
| `top_priorities` | jsonb |  | '[]'::jsonb |
| `life_chapter` | jsonb |  | '{}'::jsonb |
| `working_memory` | jsonb |  | '{}'::jsonb |
| `last_updated` | timestamp with time zone |  | now() |

### planner_context_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `payload` | jsonb |  |  |
| `updated_at` | timestamp with time zone |  | now() |

### planner_goals

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `title` | text |  |  |
| `details` | text | ✓ | ''::text |
| `horizon` | text |  | 'week'::text |
| `priority` | integer |  | 1 |
| `status` | text |  | 'active'::text |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |

### planner_milestones

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `goal_id` | uuid |  |  |
| `title` | text |  |  |
| `details` | text | ✓ | ''::text |
| `due_ts` | timestamp with time zone | ✓ |  |
| `horizon` | text |  | 'week'::text |
| `status` | text |  | 'active'::text |
| `sequence` | integer |  | 0 |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |

### preferences

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `scope` | text | ✓ |  |
| `key` | text | ✓ |  |
| `value` | jsonb | ✓ |  |
| `confidence` | numeric | ✓ |  |
| `evidence_ids` | _uuid[] | ✓ | '{}'::uuid[] |

### presence_state

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `date` | date |  | CURRENT_DATE |
| `summary` | text | ✓ |  |
| `mood_today` | text | ✓ |  |
| `open_actions` | jsonb | ✓ | '{}'::jsonb |
| `created_at` | timestamp with time zone | ✓ | now() |
| `updated_at` | timestamp with time zone | ✓ | now() |

### purpose_themes

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `theme` | text |  |  |
| `description` | text | ✓ |  |
| `anchors` | jsonb |  | '[]'::jsonb |
| `momentum` | numeric |  | 0.0 |
| `created_at` | timestamp with time zone |  | now() |

### reflection_feedback

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `reflection_id` | bigint | ✓ |  |
| `helpful` | boolean | ✓ |  |
| `comment` | text | ✓ |  |
| `created_at` | timestamp with time zone | ✓ | now() |

### relationship_state

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `trust_score` | numeric | ✓ | 0.4 |
| `attunement_score` | numeric | ✓ | 0.4 |
| `emotional_safety` | numeric | ✓ | 0.5 |
| `closeness_stage` | text | ✓ | 'Warm'::text |
| `preference_profile` | jsonb |  | '{}'::jsonb |
| `interaction_patterns` | jsonb |  | '{}'::jsonb |
| `updated_at` | timestamp with time zone |  | now() |

### rhythm_insights

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `window_start` | date | ✓ |  |
| `window_end` | date | ✓ |  |
| `pattern_type` | text | ✓ |  |
| `summary` | text | ✓ |  |
| `recommendation` | text | ✓ |  |
| `confidence` | double precision | ✓ |  |
| `created_at` | timestamp with time zone | ✓ | now() |

### rhythm_planner_alignment

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `horizon` | text |  |  |
| `recommendations` | jsonb |  |  |
| `generated_at` | timestamp with time zone |  | now() |

### salient_memories

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `user_id` | uuid |  |  |
| `session_id` | uuid | ✓ |  |
| `kind` | text |  |  |
| `key` | text |  |  |
| `value` | jsonb |  |  |
| `source_turn_id` | uuid | ✓ |  |
| `salience` | double precision |  | 0.7 |
| `created_at` | timestamp with time zone |  | now() |

### soul_values

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `value_name` | text |  |  |
| `description` | text | ✓ |  |
| `confidence` | numeric |  | 0.0 |
| `anchors` | jsonb |  | '{}'::jsonb |
| `evidence` | jsonb |  | '{}'::jsonb |
| `created_at` | timestamp with time zone |  | now() |

### surfaced_aspects

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `user_id` | uuid |  |  |
| `key` | text |  |  |
| `last_surfaced_at` | timestamp with time zone |  | now() |

### system_events

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint |  | nextval('system_events_id_seq'::regcl... |
| `ts` | timestamp with time zone | ✓ | now() |
| `person_id` | uuid | ✓ |  |
| `layer` | text | ✓ |  |
| `event` | text | ✓ |  |
| `payload` | jsonb | ✓ |  |

### system_tempo

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `phase` | text | ✓ |  |
| `tempo` | double precision | ✓ |  |
| `coherence` | double precision | ✓ |  |
| `updated_at` | timestamp with time zone | ✓ | now() |

### task_dependencies

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `task_id` | uuid |  |  |
| `depends_on_task_id` | uuid |  |  |
| `hard` | boolean |  | false |

### task_routing_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `task_id` | uuid |  |  |
| `person_id` | uuid | ✓ |  |
| `category` | text |  |  |
| `recommended_window` | text | ✓ |  |
| `reason` | text | ✓ |  |
| `forecast_snapshot` | jsonb | ✓ |  |
| `updated_at` | timestamp with time zone | ✓ | now() |

### theme_rhythm_links

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `theme` | text |  |  |
| `correlation` | double precision | ✓ |  |
| `clarity_trend` | double precision | ✓ |  |
| `energy_trend` | double precision | ✓ |  |
| `samples` | integer | ✓ | 0 |
| `updated_at` | timestamp with time zone | ✓ | now() |

### theme_states

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid | ✓ |  |
| `theme` | text |  |  |
| `rhythm_state` | jsonb | ✓ | '{}'::jsonb |
| `emotional_state` | jsonb | ✓ | '{}'::jsonb |
| `clarity_score` | double precision | ✓ | 0.0 |
| `updated_at` | timestamp with time zone | ✓ | now() |

### themes

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `name` | text | ✓ |  |
| `description` | text | ✓ |  |
| `scope` | text | ✓ |  |
| `embed` | vector | ✓ |  |
| `signals` | jsonb | ✓ |  |
| `trend` | jsonb | ✓ |  |
| `embed_vec` | vector | ✓ |  |

### thread_continuity_markers

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid |  | gen_random_uuid() |
| `person_id` | uuid |  |  |
| `thread_id` | uuid |  |  |
| `continuity_hint` | text | ✓ |  |
| `persona_stability` | jsonb |  | '{}'::jsonb |
| `last_turn_id` | uuid | ✓ |  |
| `created_at` | timestamp with time zone |  | now() |
| `updated_at` | timestamp with time zone |  | now() |

### wellness_state_cache

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `person_id` | uuid |  |  |
| `body` | jsonb | ✓ | '{}'::jsonb |
| `mind` | jsonb | ✓ | '{}'::jsonb |
| `emotion` | jsonb | ✓ | '{}'::jsonb |
| `energy` | jsonb | ✓ | '{}'::jsonb |
| `updated_at` | timestamp with time zone | ✓ | now() |


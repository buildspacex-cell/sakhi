# Sakhi Database Schema (Live from Database)

**Total Tables: 179**

Generated from production database on 2026-02-03

---

## agent_actions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| session_id | uuid | NOT NULL | FK → agent_sessions.id |
| agent_id | uuid | NOT NULL |  |
| person_id | text | NOT NULL |  |
| action_type | text | NOT NULL |  |
| parameters | jsonb | NULL |  |
| requires_approval | bool | NULL |  |
| approved_at | timestamptz | NULL |  |
| sequence | int4 | NULL |  |
| status | text | NOT NULL |  |
| sent_at | timestamptz | NULL |  |
| started_at | timestamptz | NULL |  |
| completed_at | timestamptz | NULL |  |
| result | jsonb | NULL |  |
| retry_count | int4 | NULL |  |
| error_message | text | NULL |  |
| created_at | timestamptz | NULL |  |

## agent_approval_history

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| action_type | text | NOT NULL |  |
| risk_level | text | NOT NULL |  |
| decision | text | NOT NULL |  |
| selected_option | text | NULL |  |
| user_comment | text | NULL |  |
| request_created_at | timestamptz | NOT NULL |  |
| decision_at | timestamptz | NOT NULL |  |
| response_time_seconds | float8 | NULL |  |
| task_type | text | NULL |  |
| context_summary | text | NULL |  |

## agent_approval_preferences

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK |
| auto_approve_actions | _text | NULL |  |
| approve_medium_risk | bool | NULL |  |
| notify_on_critical | bool | NULL |  |
| notification_channel | text | NULL |  |
| default_timeout_seconds | int4 | NULL |  |
| learn_from_history | bool | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## agent_approval_requests

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| request_id | text | NOT NULL | PK |
| session_id | text | NOT NULL |  |
| task_id | text | NOT NULL |  |
| person_id | uuid | NOT NULL |  |
| action_type | text | NOT NULL |  |
| action_parameters | jsonb | NOT NULL |  |
| action_description | text | NOT NULL |  |
| risk_level | text | NOT NULL |  |
| status | text | NOT NULL |  |
| context_summary | text | NULL |  |
| why_approval_needed | text | NULL |  |
| if_approved | text | NULL |  |
| if_rejected | text | NULL |  |
| options | jsonb | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| expires_at | timestamptz | NULL |  |
| resolved_at | timestamptz | NULL |  |
| resolved_by | text | NULL |  |
| screenshot_id | text | NULL |  |
| screenshot_url | text | NULL |  |

## agent_screenshots

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| session_id | uuid | NULL | FK → agent_sessions.id |
| agent_id | uuid | NOT NULL | FK → registered_agents.id |
| person_id | uuid | NOT NULL |  |
| storage_path | text | NOT NULL |  |
| storage_bucket | text | NULL |  |
| width | int4 | NULL |  |
| height | int4 | NULL |  |
| format | text | NULL |  |
| trigger | text | NULL |  |
| preceding_action_id | uuid | NULL | FK → agent_actions.id |
| analysis | jsonb | NULL |  |
| analyzed_at | timestamptz | NULL |  |
| captured_at | timestamptz | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## agent_sessions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | text | NOT NULL |  |
| agent_id | uuid | NOT NULL |  |
| task_description | text | NULL |  |
| status | text | NOT NULL |  |
| current_step | int4 | NULL |  |
| total_steps | int4 | NULL |  |
| actions_executed | int4 | NULL |  |
| timeout_at | timestamptz | NULL |  |
| started_at | timestamptz | NULL |  |
| completed_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |
| actions_failed | int4 | NULL |  |

## agent_task_plans

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| session_id | uuid | NULL | FK → agent_sessions.id |
| task_type | text | NOT NULL |  |
| task_description | text | NOT NULL |  |
| steps | jsonb | NOT NULL |  |
| context_used | jsonb | NULL |  |
| status | text | NOT NULL |  |
| current_step_index | int4 | NULL |  |
| result | jsonb | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| started_at | timestamptz | NULL |  |
| completed_at | timestamptz | NULL |  |

## agent_versions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| agent_type | text | NOT NULL | UNIQUE |
| platform | text | NOT NULL | UNIQUE |
| architecture | text | NULL |  |
| version | text | NOT NULL | UNIQUE |
| download_url | text | NULL |  |
| checksum | text | NULL |  |
| file_size_bytes | int8 | NULL |  |
| is_mandatory | bool | NULL |  |
| release_notes | text | NULL |  |
| min_required_version | text | NULL |  |
| status | text | NULL |  |
| released_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |

## analytics_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| metric | text | NOT NULL |  |
| value | float8 | NULL |  |
| period | text | NULL |  |
| computed_at | timestamptz | NULL |  |

## auth_users

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| supabase_user_id | uuid | NULL | UNIQUE |
| email | text | NOT NULL | UNIQUE |
| full_name | text | NULL |  |
| avatar_url | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| last_sign_in_at | timestamptz | NULL |  |
| onboarding_completed_at | timestamptz | NULL |  |
| deleted_at | timestamptz | NULL |  |

## behavior_log

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| behavior_type | text | NOT NULL |  |
| behavior_name | text | NOT NULL |  |
| occurred_at | timestamptz | NOT NULL |  |
| dosha_effect | text | NULL |  |
| effect_direction | text | NULL |  |
| source_text | text | NULL |  |
| source_type | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| time_of_day | text | NULL |  |
| source | text | NULL |  |
| related_entry_id | text | NULL |  |
| intensity | float8 | NULL |  |

## body_state_history

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| body_state | jsonb | NOT NULL |  |
| computed_at | timestamptz | NULL |  |
| overall_score | float8 | NULL |  |
| vata_score | float8 | NULL |  |
| pitta_score | float8 | NULL |  |
| kapha_score | float8 | NULL |  |
| ojas_level | float8 | NULL |  |
| sleep_quality | float8 | NULL |  |
| energy_level | float8 | NULL |  |

## brain_goals_themes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → profiles.user_id |
| cluster_title | text | NULL |  |
| cluster_vector | vector | NULL |  |
| supporting_entry_ids | _uuid | NULL |  |
| confidence | float8 | NULL |  |
| time_window | text | NULL |  |
| emotional_tone | jsonb | NULL |  |
| value_mapping | jsonb | NULL |  |
| identity_alignment | float8 | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## coherence_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| coherence_state | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## collective_patterns

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| pattern_type | text | NOT NULL |  |
| mean_vector | vector | NULL |  |
| std_dev_vector | vector | NULL |  |
| support_count | int4 | NOT NULL |  |
| last_updated | timestamptz | NULL |  |
| metadata | jsonb | NULL |  |

## context_recalls

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| turn_id | uuid | NULL |  |
| thread_id | uuid | NULL |  |
| stitched_summary | text | NULL |  |
| compact | jsonb | NULL |  |
| vectors | jsonb | NULL |  |
| signals | jsonb | NULL |  |
| confidence | float8 | NULL |  |
| created_at | timestamptz | NOT NULL |  |

## conversation_media

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| media_id | uuid | NOT NULL | FK → media_attachments.id |
| session_id | text | NULL |  |
| entry_id | uuid | NULL |  |
| turn_index | int4 | NULL |  |
| role | text | NOT NULL |  |
| purpose | text | NULL |  |
| created_at | timestamptz | NULL |  |

## conversation_sessions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| user_id | uuid | NOT NULL | UNIQUE |
| slug | text | NOT NULL | UNIQUE |
| title | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| tags | _text | NULL |  |
| status | text | NOT NULL |  |
| last_active_at | timestamptz | NOT NULL |  |
| turn_count | int4 | NOT NULL |  |
| summary_vec | vector | NULL |  |
| archived_at | timestamptz | NULL |  |

## conversation_state

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| last_emotion | text | NULL |  |
| dominant_theme | text | NULL |  |
| last_tone | text | NULL |  |
| clarity_level | float8 | NULL |  |
| energy_level | float8 | NULL |  |
| updated_at | timestamptz | NULL |  |

## conversation_suggestions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| suggestion | text | NOT NULL |  |
| style | text | NULL |  |
| confidence | float8 | NULL |  |
| payload | jsonb | NULL |  |
| created_at | timestamptz | NOT NULL |  |

## conversation_turns

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| user_id | uuid | NOT NULL |  |
| session_id | uuid | NOT NULL | FK → conversation_sessions.id |
| role | text | NOT NULL |  |
| text | text | NOT NULL |  |
| tone | text | NULL |  |
| archetype | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| person_id | uuid | NULL |  |
| reply | text | NULL |  |
| context_version | int4 | NOT NULL |  |
| queued_jobs | jsonb | NOT NULL |  |
| metadata | jsonb | NOT NULL |  |
| source | text | NULL |  |

## coordination_messages

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| thread_id | uuid | NOT NULL | FK → coordination_threads.id |
| sender_entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| sender_type | text | NOT NULL |  |
| message_type | text | NOT NULL |  |
| content | jsonb | NOT NULL |  |
| requires_response | bool | NULL |  |
| response_deadline | timestamptz | NULL |  |
| read_at | timestamptz | NULL |  |
| responded_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |

## coordination_threads

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| initiator_entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| recipient_entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| coordination_type | text | NOT NULL |  |
| subject | text | NULL |  |
| context | jsonb | NOT NULL |  |
| proposed_options | jsonb | NULL |  |
| status | text | NOT NULL |  |
| outcome | jsonb | NULL |  |
| related_event_id | uuid | NULL |  |
| related_transaction_id | uuid | NULL |  |
| relationship_context | jsonb | NULL |  |
| priority | text | NULL |  |
| expires_at | timestamptz | NULL |  |
| completed_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## crystallization_log

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| crystallized_pattern_id | uuid | NULL | FK → crystallized_patterns.id |
| pattern_type | text | NOT NULL |  |
| pattern_value | text | NOT NULL |  |
| occurrence_count | int4 | NULL |  |
| distinct_days | int4 | NULL |  |
| confidence | float8 | NULL |  |
| span_days | int4 | NULL |  |
| threshold_config | jsonb | NULL |  |
| evidence_ids | _uuid | NULL |  |
| action | text | NULL |  |
| crystallized_at | timestamptz | NULL |  |

## crystallized_patterns

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → profiles.user_id |
| pattern_type | text | NOT NULL | UNIQUE |
| pattern_value | text | NOT NULL | UNIQUE |
| sub_topic | text | NULL |  |
| summary | text | NULL |  |
| constitution_relevance | text | NULL |  |
| evidence_ids | _uuid | NULL |  |
| evidence_snippets | jsonb | NULL |  |
| mention_count | int4 | NOT NULL |  |
| distinct_days | int4 | NOT NULL |  |
| confidence | float8 | NOT NULL |  |
| threshold_met_at | timestamptz | NULL |  |
| trajectory | text | NULL |  |
| trajectory_data | jsonb | NULL |  |
| status | text | NOT NULL |  |
| first_seen | timestamptz | NOT NULL |  |
| last_seen | timestamptz | NOT NULL |  |
| crystallized_at | timestamptz | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## daily_alignment_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| alignment_map | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## daily_closure_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| closure_date | date | NOT NULL | UNIQUE |
| completed | jsonb | NULL |  |
| pending | jsonb | NULL |  |
| signals | jsonb | NULL |  |
| summary | text | NULL |  |
| generated_at | timestamptz | NULL |  |

## daily_reflection_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| reflection_date | date | NOT NULL | PK |
| summary | jsonb | NOT NULL |  |
| generated_at | timestamptz | NULL |  |

## debug_traces

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| trace_id | text | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| flow | text | NOT NULL |  |
| payload | jsonb | NOT NULL |  |
| human_narrative | text | NULL |  |
| plain_layers | jsonb | NULL |  |
| finished_at | timestamptz | NULL |  |
| success | bool | NULL |  |
| summary | jsonb | NULL |  |

## device_link_codes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| code | text | NOT NULL | PK |
| device_id | text | NOT NULL |  |
| platform | text | NOT NULL |  |
| architecture | text | NULL |  |
| agent_type | text | NOT NULL |  |
| agent_name | text | NULL |  |
| status | text | NOT NULL |  |
| person_id | uuid | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| expires_at | timestamptz | NOT NULL |  |
| confirmed_at | timestamptz | NULL |  |

## elemental_signal_stm

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| source_signal_id | uuid | NOT NULL |  |
| source_type | text | NOT NULL |  |
| dimension | text | NOT NULL |  |
| earth | numeric | NOT NULL |  |
| water | numeric | NOT NULL |  |
| fire | numeric | NOT NULL |  |
| air | numeric | NOT NULL |  |
| ether | numeric | NOT NULL |  |
| confidence | numeric | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| expires_at | timestamptz | NOT NULL |  |
| magnitude | numeric | NOT NULL |  |

## elemental_summary_weekly

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE |
| week_start | date | NOT NULL | UNIQUE |
| elements | jsonb | NULL |  |
| dosha_balance | jsonb | NULL |  |
| signals_count | int4 | NULL |  |
| confidence | float8 | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## events

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| user_id | uuid | NOT NULL |  |
| type | text | NOT NULL |  |
| v | int4 | NOT NULL |  |
| ts | timestamptz | NOT NULL |  |
| idempotency_key | text | NULL |  |
| payload | jsonb | NOT NULL |  |
| occurred_at | timestamptz | NOT NULL |  |
| event_type | text | NOT NULL |  |
| response | jsonb | NULL |  |
| created_at | timestamptz | NOT NULL |  |

## facts

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE |
| scope | text | NOT NULL | UNIQUE |
| key | text | NOT NULL | UNIQUE |
| value | jsonb | NOT NULL |  |
| confidence | float8 | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |
| embedding | vector | NULL |  |

## focus_events

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| session_id | uuid | NOT NULL | FK → focus_sessions.id |
| ts | timestamptz | NOT NULL |  |
| event_type | text | NOT NULL |  |
| content | jsonb | NOT NULL |  |
| rhythm_state | jsonb | NOT NULL |  |
| task_state | jsonb | NOT NULL |  |
| emotion_state | jsonb | NOT NULL |  |

## focus_path_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| path_date | date | NOT NULL | UNIQUE |
| anchor_step | text | NULL |  |
| progress_step | text | NULL |  |
| closure_step | text | NULL |  |
| intent_source | text | NULL |  |
| generated_at | timestamptz | NULL |  |

## focus_sessions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| task_id | uuid | NULL | FK → planned_items.id |
| mode | text | NULL |  |
| start_time | timestamptz | NOT NULL |  |
| end_time | timestamptz | NULL |  |
| estimated_duration | int4 | NULL |  |
| actual_duration | int4 | NULL |  |
| completion_score | numeric | NULL |  |
| session_quality | jsonb | NOT NULL |  |
| session_start_state | jsonb | NOT NULL |  |
| status | text | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## forecast_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| forecast_state | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## goal_history

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| goal_id | uuid | NULL | FK → goals.id |
| person_id | uuid | NULL | FK → profiles.user_id |
| previous_title | text | NULL |  |
| previous_description | text | NULL |  |
| revised_title | text | NULL |  |
| revised_description | text | NULL |  |
| reason | text | NULL |  |
| created_at | timestamptz | NULL |  |

## goals

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| parent_goal_id | uuid | NULL | FK → goals.id |
| title | text | NULL |  |
| description | text | NULL |  |
| horizon | text | NULL |  |
| status | text | NULL |  |
| progress | numeric | NULL |  |
| evolution_score | float8 | NULL |  |
| last_revised | timestamptz | NULL |  |
| updated_at | timestamptz | NOT NULL |  |
| type | text | NULL |  |
| priority | int4 | NULL |  |
| due_at | timestamptz | NULL |  |
| meta | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |
| completed_at | timestamptz | NULL |  |

## growth_daily_checkins

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → profiles.user_id |
| checkin_date | date | NOT NULL | UNIQUE |
| energy | numeric | NULL |  |
| mood | text | NULL |  |
| reflection | text | NULL |  |
| plan_adjustment | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## growth_habit_logs

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| habit_id | uuid | NOT NULL | FK → growth_habits.id |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| logged_at | timestamptz | NOT NULL |  |
| micro_score | numeric | NOT NULL |  |
| mood | text | NULL |  |
| note | text | NULL |  |
| payload | jsonb | NOT NULL |  |

## growth_habits

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → profiles.user_id |
| label | text | NOT NULL | UNIQUE |
| cadence | jsonb | NOT NULL |  |
| intent_source | text | NULL |  |
| streak_count | int4 | NOT NULL |  |
| micro_progress | numeric | NOT NULL |  |
| confidence | numeric | NOT NULL |  |
| last_logged | timestamptz | NULL |  |
| active | bool | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## growth_task_confidence_events

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| task_id | uuid | NULL |  |
| task_label | text | NULL |  |
| confidence_before | numeric | NULL |  |
| confidence_after | numeric | NULL |  |
| delta | numeric | NULL |  |
| source | text | NULL |  |
| payload | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## health_data_sync

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| source | text | NOT NULL |  |
| data_type | text | NOT NULL |  |
| data | jsonb | NOT NULL |  |
| recorded_at | timestamptz | NOT NULL |  |
| synced_at | timestamptz | NULL |  |
| processed | bool | NULL |  |
| processed_at | timestamptz | NULL |  |

## identity_drift_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| identity_state | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## inner_conflict_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| conflict_state | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## inner_dialogue_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| dialogue | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## insight

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | text | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| from_ids | _text | NOT NULL |  |
| kind | text | NOT NULL |  |
| message | text | NOT NULL |  |
| why | jsonb | NULL |  |
| actions | jsonb | NULL |  |
| confidence | numeric | NULL |  |
| ts | timestamptz | NOT NULL |  |

## insights_queue

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → persons.id |
| insight | jsonb | NOT NULL |  |
| priority | text | NULL |  |
| timing_hint | text | NULL |  |
| delivered | bool | NULL |  |
| created_at | timestamptz | NULL |  |

## intent_evolution

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| intent_name | text | NOT NULL | PK |
| strength | float8 | NULL |  |
| emotional_alignment | float8 | NULL |  |
| trend | text | NULL |  |
| last_seen | timestamptz | NULL |  |
| first_seen | timestamptz | NULL |  |

## intents

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| user_id | uuid | NOT NULL | FK → users.id |
| source_entry_id | uuid | NULL | FK → journal_entries.id |
| title | text | NOT NULL |  |
| raw_input | text | NULL |  |
| intent_type | text | NOT NULL |  |
| domain | text | NULL |  |
| timeline | text | NOT NULL |  |
| target_date | date | NULL |  |
| priority | int2 | NULL |  |
| status | text | NOT NULL |  |
| clarity_score | numeric | NULL |  |
| user_permission | bool | NULL |  |
| proposed_plan | jsonb | NULL |  |
| context_snapshot | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## intervention_checkins

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| plan_id | uuid | NOT NULL | UNIQUE, FK → intervention_plans.id |
| scheduled_date | date | NOT NULL | UNIQUE |
| status | text | NULL |  |
| completed_count | int4 | NULL |  |
| notes | text | NULL |  |
| mood_before | float8 | NULL |  |
| mood_after | float8 | NULL |  |
| checked_in_at | timestamptz | NULL |  |
| nudge_sent | bool | NULL |  |
| nudge_sent_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |

## intervention_nudges

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| plan_id | uuid | NULL | FK → intervention_plans.id |
| checkin_id | uuid | NULL | FK → intervention_checkins.id |
| nudge_type | text | NOT NULL |  |
| message | text | NOT NULL |  |
| channel | text | NULL |  |
| sent_at | timestamptz | NULL |  |
| read_at | timestamptz | NULL |  |
| acted_on | bool | NULL |  |
| acted_at | timestamptz | NULL |  |

## intervention_outcomes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| intervention_type | text | NOT NULL |  |
| intervention_name | text | NOT NULL |  |
| occurred_at | timestamptz | NULL |  |
| was_effective | bool | NULL |  |
| effectiveness_score | float8 | NULL |  |
| symptom_addressed | text | NULL |  |
| related_dosha | text | NULL |  |
| notes | text | NULL |  |
| created_at | timestamptz | NULL |  |

## intervention_plans

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| intervention_type | text | NOT NULL |  |
| intervention_name | text | NOT NULL |  |
| description | text | NULL |  |
| schedule_type | text | NOT NULL |  |
| schedule_days | _int4 | NULL |  |
| target_per_day | int4 | NULL |  |
| start_date | date | NOT NULL |  |
| end_date | date | NULL |  |
| duration_days | int4 | NULL |  |
| target_symptom | text | NULL |  |
| target_dosha | text | NULL |  |
| baseline_severity | float8 | NULL |  |
| status | text | NULL |  |
| total_scheduled | int4 | NULL |  |
| total_completed | int4 | NULL |  |
| current_streak | int4 | NULL |  |
| longest_streak | int4 | NULL |  |
| notes | text | NULL |  |
| recommendation_id | uuid | NULL |  |
| conversation_id | uuid | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## journal_embeddings

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| entry_id | uuid | NOT NULL | PK, FK → journal_entries.id |
| model | text | NOT NULL |  |
| embedding | vector | NULL |  |
| created_at | timestamptz | NULL |  |
| embedding_vec | vector | NULL |  |
| content_hash | text | NULL |  |

## journal_entries

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| user_id | uuid | NOT NULL | FK → persons.id |
| raw_encrypted | bytea | NULL |  |
| cleaned | text | NULL |  |
| facets | jsonb | NOT NULL |  |
| salience | float4 | NOT NULL |  |
| ts | timestamptz | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |
| content | text | NULL |  |
| title | text | NULL |  |
| fts | tsvector | NULL |  |
| raw | text | NULL |  |
| encrypted_preview | text | NULL |  |
| facets_v2 | jsonb | NULL |  |
| cleaned_tsv | tsvector | NULL |  |
| narrative | jsonb | NOT NULL |  |
| debug_payload | jsonb | NOT NULL |  |
| layer | text | NULL |  |
| tags | _text | NULL |  |
| source_ref | jsonb | NULL |  |
| mood | text | NULL |  |
| person_id | uuid | NULL |  |
| processing_state | text | NOT NULL |  |
| processing_attempts | int4 | NOT NULL |  |
| processed_at | timestamptz | NULL |  |
| processing_error | jsonb | NULL |  |
| ack_text | text | NULL |  |
| worker_enrichment | jsonb | NULL |  |
| input_type | text | NULL |  |
| client_context | jsonb | NULL |  |
| language | text | NULL |  |
| timezone | text | NULL |  |
| user_tags | _text | NULL |  |

## journal_inference

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| entry_id | uuid | NOT NULL | FK → journal_entries.id |
| container | text | NOT NULL |  |
| payload | jsonb | NOT NULL |  |
| confidence | numeric | NULL |  |
| inference_type | text | NOT NULL |  |
| source | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |

## journal_links

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| src_id | uuid | NOT NULL | PK, FK → journal_entries.id |
| dst_id | uuid | NOT NULL | PK, FK → journal_entries.id |
| strength | numeric | NOT NULL |  |
| created_at | timestamptz | NULL |  |

## journal_themes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| user_id | uuid | NOT NULL |  |
| theme | text | NOT NULL |  |
| time_window | text | NOT NULL |  |
| metrics | jsonb | NOT NULL |  |
| created_at | timestamptz | NULL |  |
| description | text | NULL |  |
| domain | text | NULL |  |
| examples | jsonb | NULL |  |

## journey_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| scope | text | NOT NULL | PK |
| payload | jsonb | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## learning_runs

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| run_type | text | NOT NULL |  |
| trigger_reason | text | NULL |  |
| behaviors_processed | int4 | NULL |  |
| symptoms_processed | int4 | NULL |  |
| patterns_detected | int4 | NULL |  |
| patterns_strengthened | int4 | NULL |  |
| preferences_updated | int4 | NULL |  |
| started_at | timestamptz | NULL |  |
| completed_at | timestamptz | NULL |  |
| duration_ms | int4 | NULL |  |
| status | text | NULL |  |
| error_message | text | NULL |  |

## long_running_missions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| title | text | NOT NULL |  |
| description | text | NULL |  |
| category | text | NULL |  |
| success_criteria | jsonb | NULL |  |
| plan_document | text | NULL |  |
| target_end_date | date | NULL |  |
| actual_end_date | date | NULL |  |
| status | text | NULL |  |
| health | text | NULL |  |
| strategy_notes | text | NULL |  |
| lessons_learned | jsonb | NULL |  |
| progress_pct | int4 | NULL |  |
| metrics | jsonb | NULL |  |
| conversation_id | uuid | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## media_attachments

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | text | NOT NULL |  |
| media_type | text | NOT NULL |  |
| mime_type | text | NOT NULL |  |
| filename | text | NULL |  |
| file_size_bytes | int4 | NULL |  |
| storage_provider | text | NOT NULL |  |
| storage_path | text | NOT NULL |  |
| thumbnail_path | text | NULL |  |
| extracted_text | text | NULL |  |
| description | text | NULL |  |
| analysis | jsonb | NULL |  |
| source | text | NULL |  |
| context | text | NULL |  |
| status | text | NULL |  |
| processed_at | timestamptz | NULL |  |
| error_message | text | NULL |  |
| width | int4 | NULL |  |
| height | int4 | NULL |  |
| duration_seconds | float8 | NULL |  |
| metadata | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## memory_context_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE |
| window_kind | text | NOT NULL | UNIQUE |
| entries | jsonb | NOT NULL |  |
| rhythm_state | jsonb | NOT NULL |  |
| persona_snapshot | jsonb | NOT NULL |  |
| task_window | jsonb | NOT NULL |  |
| version | int4 | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |
| merged_context_vector | vector | NULL |  |

## memory_edges

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| from_node | uuid | NULL | UNIQUE, FK → memory_nodes.id |
| to_node | uuid | NULL | UNIQUE, FK → memory_nodes.id |
| relation | text | NULL | UNIQUE |
| weight | float8 | NULL |  |
| updated_at | timestamptz | NULL |  |
| relevance | float8 | NULL |  |
| created_at | timestamptz | NULL |  |
| evidence | jsonb | NULL |  |
| occurrence_count | int4 | NULL |  |

## memory_episodic

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| user_id | text | NOT NULL |  |
| record | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| soul | jsonb | NULL |  |
| soul_shadow | jsonb | NULL |  |
| soul_light | jsonb | NULL |  |
| soul_conflict | jsonb | NULL |  |
| soul_friction | jsonb | NULL |  |
| emotion_loop | jsonb | NULL |  |
| content_hash | text | NULL |  |
| vector_vec | vector | NULL |  |
| context_tags | jsonb | NULL |  |
| entry_id | uuid | NULL |  |
| person_id | uuid | NULL |  |
| triage | jsonb | NULL |  |
| time_scope | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |
| text | text | NULL |  |
| rhythm_state | jsonb | NULL |  |
| emotional_state | jsonb | NULL |  |
| ts | timestamptz | NULL |  |
| state_vector | jsonb | NULL |  |
| guna_vector | jsonb | NULL |  |

## memory_monthly_recaps

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → profiles.user_id |
| month_scope | daterange | NOT NULL | UNIQUE |
| summary | jsonb | NOT NULL |  |
| highlights | text | NULL |  |
| top_themes | jsonb | NOT NULL |  |
| chapter_hint | text | NULL |  |
| drift_score | numeric | NOT NULL |  |
| compression | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## memory_nodes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| node_kind | text | NULL | UNIQUE |
| label | text | NULL | UNIQUE |
| data | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |
| weight | float8 | NULL |  |
| updated_at | timestamptz | NULL |  |
| last_referenced_at | timestamptz | NULL |  |

## memory_semantic_rollups

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → profiles.user_id |
| source_id | uuid | NOT NULL | UNIQUE |
| source_kind | text | NOT NULL | UNIQUE |
| semantic_summary | text | NOT NULL |  |
| strength | numeric | NOT NULL |  |
| payload | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## memory_short_term

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| user_id | text | NOT NULL |  |
| record | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| soul | jsonb | NULL |  |
| soul_shadow | jsonb | NULL |  |
| soul_light | jsonb | NULL |  |
| content_hash | text | NULL |  |
| vector_vec | vector | NULL |  |
| expires_at | timestamptz | NOT NULL |  |
| entry_id | uuid | NULL |  |
| text | text | NULL |  |
| layer | text | NULL |  |
| triage | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |
| person_id | text | NULL |  |

## memory_strength_events

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| event_kind | text | NOT NULL |  |
| target | text | NOT NULL |  |
| weight | numeric | NOT NULL |  |
| payload | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## memory_theme_drift_events

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| horizon | text | NOT NULL |  |
| from_theme | text | NULL |  |
| to_theme | text | NULL |  |
| drift_score | numeric | NOT NULL |  |
| evidence | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## memory_weekly_signals

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → profiles.user_id |
| week_start | date | NOT NULL | UNIQUE |
| week_end | date | NOT NULL |  |
| episodic_stats | jsonb | NOT NULL |  |
| theme_stats | jsonb | NOT NULL |  |
| contrast_stats | jsonb | NOT NULL |  |
| delta_stats | jsonb | NOT NULL |  |
| confidence | numeric | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| weekly_contrast | jsonb | NULL |  |
| dimension_states | jsonb | NULL |  |
| weekly_salience | jsonb | NULL |  |
| weekly_body_notes | jsonb | NULL |  |

## memory_weekly_summaries

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → profiles.user_id |
| week_start | date | NOT NULL | UNIQUE |
| week_end | date | NOT NULL |  |
| summary | jsonb | NOT NULL |  |
| highlights | text | NULL |  |
| top_themes | jsonb | NOT NULL |  |
| drift_score | numeric | NOT NULL |  |
| semantic_notes | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## mesh_coordination

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| conversation_id | uuid | NOT NULL | UNIQUE |
| initiator_sakhi_id | uuid | NOT NULL | FK → sakhi_registry.sakhi_id |
| target_sakhi_id | uuid | NOT NULL | FK → sakhi_registry.sakhi_id |
| coordination_type | text | NOT NULL |  |
| event_type | text | NULL |  |
| request_context | text | NULL |  |
| timeframe_start | timestamptz | NULL |  |
| timeframe_end | timestamptz | NULL |  |
| preferred_duration_minutes | int4 | NULL |  |
| status | text | NULL |  |
| initiator_availability | jsonb | NULL |  |
| target_availability | jsonb | NULL |  |
| proposed_time | timestamptz | NULL |  |
| proposed_location | text | NULL |  |
| proposed_location_data | jsonb | NULL |  |
| proposal_reasoning | text | NULL |  |
| initiator_response | text | NULL |  |
| target_response | text | NULL |  |
| initiator_event_id | uuid | NULL |  |
| target_event_id | uuid | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |
| expires_at | timestamptz | NULL |  |

## mesh_endpoints

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| sakhi_id | text | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| endpoint_url | text | NOT NULL |  |
| display_name | text | NULL |  |
| public_key | text | NULL |  |
| last_seen | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |

## mesh_message_queue

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| message_id | text | NOT NULL | PK |
| from_sakhi_id | text | NOT NULL |  |
| to_sakhi_id | text | NOT NULL |  |
| message_type | text | NOT NULL |  |
| payload | jsonb | NULL |  |
| reply_to | text | NULL |  |
| created_at | timestamptz | NULL |  |
| last_attempt | timestamptz | NULL |  |
| attempts | int4 | NULL |  |
| delivered_at | timestamptz | NULL |  |
| max_retries | int4 | NULL |  |
| next_retry_at | timestamptz | NULL |  |
| status | text | NULL |  |
| error_message | text | NULL |  |
| response_received_at | timestamptz | NULL |  |
| response_payload | jsonb | NULL |  |

## mesh_messages

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| from_sakhi_id | uuid | NOT NULL | FK → sakhi_registry.sakhi_id |
| to_sakhi_id | uuid | NOT NULL | FK → sakhi_registry.sakhi_id |
| message_type | text | NOT NULL |  |
| payload | jsonb | NOT NULL |  |
| conversation_id | uuid | NULL |  |
| in_reply_to | uuid | NULL |  |
| status | text | NULL |  |
| created_at | timestamptz | NULL |  |
| delivered_at | timestamptz | NULL |  |
| processed_at | timestamptz | NULL |  |

## mesh_private_keys

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| sakhi_id | text | NOT NULL | PK |
| encrypted_key | text | NOT NULL |  |
| created_at | timestamptz | NULL |  |
| rotated_at | timestamptz | NULL |  |

## mesh_response_correlation

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| request_message_id | text | NOT NULL | UNIQUE |
| response_message_id | text | NOT NULL | UNIQUE |
| correlated_at | timestamptz | NULL |  |

## meta_reflection_scores

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| helpfulness | numeric | NULL |  |
| clarity | numeric | NULL |  |
| tone_feedback | text | NULL |  |
| updated_at | timestamp | NULL |  |

## meta_reflections

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → persons.id |
| period | text | NULL |  |
| summary | text | NULL |  |
| insights | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |

## micro_goals

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → profiles.user_id |
| source | text | NOT NULL |  |
| normalized | text | NOT NULL |  |
| micro_steps | jsonb | NOT NULL |  |
| confidence | float8 | NOT NULL |  |
| blocked | bool | NOT NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## micro_journey_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| journey | jsonb | NOT NULL |  |
| flow_count | int4 | NOT NULL |  |
| rhythm_slot | text | NULL |  |
| generated_at | timestamptz | NOT NULL |  |

## micro_momentum_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| nudge_date | date | NOT NULL | UNIQUE |
| nudge | text | NULL |  |
| reason | text | NULL |  |
| generated_at | timestamptz | NULL |  |

## micro_recovery_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| recovery_date | date | NOT NULL | UNIQUE |
| nudge | text | NULL |  |
| reason | text | NULL |  |
| generated_at | timestamptz | NULL |  |

## mini_flow_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| flow_date | date | NOT NULL | UNIQUE |
| warmup_step | text | NULL |  |
| focus_block_step | text | NULL |  |
| closure_step | text | NULL |  |
| optional_reward | text | NULL |  |
| source | text | NULL |  |
| generated_at | timestamptz | NULL |  |
| rhythm_slot | text | NULL |  |

## mission_checkpoints

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| mission_id | uuid | NOT NULL | FK → long_running_missions.id |
| checkpoint_date | date | NOT NULL |  |
| checkpoint_type | text | NOT NULL |  |
| metrics_snapshot | jsonb | NULL |  |
| progress_pct | int4 | NULL |  |
| health | text | NULL |  |
| analysis | text | NULL |  |
| recommendations | _text | NULL |  |
| risks | _text | NULL |  |
| adjustments_approved | jsonb | NULL |  |
| user_feedback | text | NULL |  |
| created_at | timestamptz | NULL |  |

## mission_data

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| mission_id | uuid | NULL | FK → long_running_missions.id |
| person_id | uuid | NOT NULL | FK → persons.id |
| record_type | text | NOT NULL |  |
| data | jsonb | NOT NULL |  |
| record_date | date | NULL |  |
| source | text | NULL |  |
| created_at | timestamptz | NULL |  |

## mission_phases

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| mission_id | uuid | NOT NULL | FK → long_running_missions.id |
| phase_number | int4 | NOT NULL |  |
| name | text | NOT NULL |  |
| objective | text | NULL |  |
| start_date | date | NOT NULL |  |
| target_end_date | date | NOT NULL |  |
| actual_end_date | date | NULL |  |
| status | text | NULL |  |
| expected_outcomes | jsonb | NULL |  |
| actual_outcomes | jsonb | NULL |  |
| requires_approval | bool | NULL |  |
| approved_at | timestamptz | NULL |  |
| approved_by | text | NULL |  |
| adjustments_made | _text | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## mission_plan_history

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| mission_id | uuid | NOT NULL | FK → long_running_missions.id |
| plan_document | text | NULL |  |
| changed_at | timestamptz | NULL |  |
| change_summary | text | NULL |  |
| changed_by | text | NULL |  |

## mission_scheduled_actions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| mission_id | uuid | NOT NULL | FK → long_running_missions.id |
| weekly_plan_id | uuid | NULL | FK → mission_weekly_plans.id |
| person_id | uuid | NOT NULL | FK → persons.id |
| action_type | text | NOT NULL |  |
| description | text | NOT NULL |  |
| instructions | jsonb | NULL |  |
| scheduled_date | date | NOT NULL |  |
| scheduled_time | time | NULL |  |
| deadline | timestamptz | NULL |  |
| trigger_type | text | NULL |  |
| cron_expression | text | NULL |  |
| trigger_condition | text | NULL |  |
| status | text | NULL |  |
| agent_session_id | uuid | NULL |  |
| started_at | timestamptz | NULL |  |
| completed_at | timestamptz | NULL |  |
| outcome | jsonb | NULL |  |
| success | bool | NULL |  |
| error_message | text | NULL |  |
| effectiveness_score | numeric | NULL |  |
| notes | text | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## mission_weekly_plans

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| mission_id | uuid | NOT NULL | FK → long_running_missions.id |
| phase_id | uuid | NULL | FK → mission_phases.id |
| week_number | int4 | NOT NULL |  |
| week_start | date | NOT NULL |  |
| week_end | date | NOT NULL |  |
| objectives | _text | NULL |  |
| tasks | jsonb | NULL |  |
| status | text | NULL |  |
| review_completed | bool | NULL |  |
| review_notes | text | NULL |  |
| what_worked | _text | NULL |  |
| what_didnt | _text | NULL |  |
| adjustments_for_next | _text | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## model_adjustments

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| pattern_type | text | NOT NULL |  |
| delta | _float8 | NULL |  |
| applied_at | timestamptz | NULL |  |
| learning_rate | float8 | NULL |  |
| notes | text | NULL |  |

## morning_ask_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| ask_date | date | NOT NULL | UNIQUE |
| question | text | NULL |  |
| reason | text | NULL |  |
| generated_at | timestamptz | NULL |  |

## morning_momentum_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| momentum_date | date | NOT NULL | UNIQUE |
| momentum_hint | text | NULL |  |
| suggested_start | text | NULL |  |
| reason | text | NULL |  |
| generated_at | timestamptz | NULL |  |

## morning_preview_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → profiles.user_id |
| preview_date | date | NOT NULL | UNIQUE |
| focus_areas | jsonb | NULL |  |
| key_tasks | jsonb | NULL |  |
| reminders | jsonb | NULL |  |
| rhythm_hint | text | NULL |  |
| summary | text | NULL |  |
| generated_at | timestamptz | NULL |  |

## narrative_arc_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, UNIQUE, FK → profiles.user_id |
| life_arcs | jsonb | NULL |  |
| micro_arcs | jsonb | NULL |  |
| active_arcs | jsonb | NULL |  |
| arc_states | jsonb | NULL |  |
| arc_progress | jsonb | NULL |  |
| arc_conflicts | jsonb | NULL |  |
| arc_breakthroughs | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## narrative_seasons

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| season | text | NOT NULL |  |
| hints | jsonb | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## narrative_stories

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| narrative | text | NOT NULL |  |
| season | text | NULL |  |
| patterns_success | jsonb | NOT NULL |  |
| patterns_struggle | jsonb | NOT NULL |  |
| identity_snapshot | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## narratives

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| kind | text | NOT NULL |  |
| summary | text | NOT NULL |  |
| signals | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## nudge_log

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| person_id | uuid | NULL | FK → profiles.user_id |
| category | text | NOT NULL |  |
| message | text | NOT NULL |  |
| forecast_snapshot | jsonb | NOT NULL |  |
| sent_at | timestamptz | NULL |  |

## parsed_documents

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| media_id | uuid | NOT NULL | FK → media_attachments.id |
| person_id | text | NOT NULL |  |
| document_type | text | NULL |  |
| title | text | NULL |  |
| full_text | text | NULL |  |
| pages | jsonb | NULL |  |
| extracted_data | jsonb | NULL |  |
| search_vector | tsvector | NULL |  |
| embedding | vector | NULL |  |
| created_at | timestamptz | NULL |  |

## pattern_occurrences

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| pattern_type | text | NOT NULL |  |
| pattern_value | text | NOT NULL |  |
| episode_id | uuid | NULL |  |
| entry_id | uuid | NULL |  |
| snippet | text | NULL |  |
| confidence | float8 | NULL |  |
| sentiment | float8 | NULL |  |
| detected_at | timestamptz | NULL |  |

## pattern_sense_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| patterns | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## pattern_stats

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| pattern_type | text | NOT NULL |  |
| metric | text | NOT NULL |  |
| value | float8 | NULL |  |
| confidence | float8 | NULL |  |
| window_scope | text | NULL |  |
| created_at | timestamptz | NULL |  |

## person_profile_map

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → persons.id |
| profile_user_id | uuid | NULL | UNIQUE, FK → profiles.user_id |

## persona_evolution

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| current_mode | text | NULL |  |
| drift_score | numeric | NOT NULL |  |
| evolution_path | jsonb | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## persona_modes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → profiles.user_id |
| mode_name | text | NULL |  |
| activation_score | float8 | NULL |  |
| last_activated | timestamptz | NULL |  |

## persona_traits

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| style_profile | jsonb | NULL |  |
| last_updated | timestamptz | NULL |  |
| sample_conversations | int4 | NULL |  |
| dominant_emotion | text | NULL |  |
| tone_bias | text | NULL |  |
| expressiveness | float8 | NULL |  |
| humor | float8 | NULL |  |
| reflectiveness | float8 | NULL |  |
| warmth | float8 | NULL |  |

## personal_embeddings

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | UNIQUE, FK → persons.id |
| label | text | NULL | UNIQUE |
| content | text | NULL |  |
| embedding | vector | NULL |  |
| updated_at | timestamptz | NULL |  |

## personal_model

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, UNIQUE, FK → persons.id |
| data | jsonb | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |
| body_state | jsonb | NULL |  |
| mind_state | jsonb | NULL |  |
| emotion_state | jsonb | NULL |  |
| goals_state | jsonb | NULL |  |
| rhythm_state | jsonb | NULL |  |
| short_term | jsonb | NULL |  |
| long_term | jsonb | NULL |  |
| summary_text | text | NULL |  |
| last_seen | timestamptz | NULL |  |
| last_reflection | timestamptz | NULL |  |
| coherence | numeric | NULL |  |
| short_term_vector | jsonb | NULL |  |
| emotion | text | NULL |  |
| relationship_state | jsonb | NULL |  |
| soul_state | jsonb | NULL |  |
| soul_vector | vector | NULL |  |
| soul_shadow | jsonb | NULL |  |
| soul_light | jsonb | NULL |  |
| soul_conflicts | jsonb | NULL |  |
| soul_friction | jsonb | NULL |  |
| emotion_soul_rhythm_state | jsonb | NULL |  |
| identity_momentum_state | jsonb | NULL |  |
| internal_decision_graph | jsonb | NULL |  |
| identity_timeline | jsonb | NULL |  |
| persona_evolution_state | jsonb | NULL |  |
| coherence_report | jsonb | NULL |  |
| narrative_arcs | jsonb | NULL |  |
| pattern_sense | jsonb | NULL |  |
| inner_dialogue_state | jsonb | NULL |  |
| identity_state | jsonb | NULL |  |
| conflict_state | jsonb | NULL |  |
| coherence_state | jsonb | NULL |  |
| forecast_state | jsonb | NULL |  |
| tone_state | jsonb | NULL |  |
| nudge_state | jsonb | NULL |  |
| empathy_state | jsonb | NULL |  |
| daily_reflection_state | jsonb | NULL |  |
| closure_state | jsonb | NULL |  |
| morning_preview_state | jsonb | NULL |  |
| morning_ask_state | jsonb | NULL |  |
| morning_momentum_state | jsonb | NULL |  |
| micro_momentum_state | jsonb | NULL |  |
| micro_recovery_state | jsonb | NULL |  |
| focus_path_state | jsonb | NULL |  |
| mini_flow_state | jsonb | NULL |  |
| mini_flow_rhythm_slot | text | NULL |  |
| longitudinal_state | jsonb | NOT NULL |  |
| alignment_state | jsonb | NULL |  |
| rhythm_soul_state | jsonb | NULL |  |
| soul_narrative | jsonb | NULL |  |
| operating_system | jsonb | NULL |  |
| life_context | jsonb | NULL |  |
| decision_profile | jsonb | NULL |  |

## personal_model_elemental

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK |
| baseline | jsonb | NOT NULL |  |
| volatility | jsonb | NOT NULL |  |
| recovery_rate | jsonb | NOT NULL |  |
| coupling | jsonb | NOT NULL |  |
| confidence | numeric | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## personal_model_energy

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK |
| baseline | jsonb | NOT NULL |  |
| volatility | jsonb | NOT NULL |  |
| recovery_profile | jsonb | NOT NULL |  |
| circulation_stability | jsonb | NOT NULL |  |
| confidence | numeric | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## personal_os_brain

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| goals_state | jsonb | NOT NULL |  |
| rhythm_state | jsonb | NOT NULL |  |
| emotional_state | jsonb | NOT NULL |  |
| identity_state | jsonb | NOT NULL |  |
| relationship_state | jsonb | NOT NULL |  |
| environment_state | jsonb | NOT NULL |  |
| habits_state | jsonb | NOT NULL |  |
| focus_state | jsonb | NOT NULL |  |
| friction_points | jsonb | NOT NULL |  |
| top_priorities | jsonb | NOT NULL |  |
| life_chapter | jsonb | NOT NULL |  |
| working_memory | jsonb | NOT NULL |  |
| last_updated | timestamptz | NOT NULL |  |

## personal_patterns

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE |
| cause_type | text | NOT NULL | UNIQUE |
| cause_value | text | NOT NULL | UNIQUE |
| effect_type | text | NOT NULL | UNIQUE |
| effect_value | text | NOT NULL | UNIQUE |
| correlation_strength | float8 | NOT NULL |  |
| confidence | float8 | NOT NULL |  |
| observation_count | int4 | NOT NULL |  |
| ayurvedic_explanation | text | NULL |  |
| related_dosha | text | NULL |  |
| first_observed_at | timestamptz | NOT NULL |  |
| last_observed_at | timestamptz | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## persons

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| created_at | timestamptz | NOT NULL |  |

## planned_items

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → persons.id |
| scope | text | NULL |  |
| label | text | NULL |  |
| payload | jsonb | NULL |  |
| due_ts | timestamptz | NULL |  |
| recurrence | jsonb | NULL |  |
| linked_goal_id | uuid | NULL | FK → goals.id |
| goal_id | uuid | NULL | FK → planner_goals.id |
| milestone_id | uuid | NULL | FK → planner_milestones.id |
| status | text | NOT NULL |  |
| priority | int4 | NOT NULL |  |
| energy | text | NULL |  |
| ease | int4 | NULL |  |
| horizon | text | NULL |  |
| origin_id | text | NULL | UNIQUE |
| meta | jsonb | NULL |  |

## planner_context_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| payload | jsonb | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## planner_goals

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| title | text | NOT NULL |  |
| details | text | NULL |  |
| horizon | text | NOT NULL |  |
| priority | int4 | NOT NULL |  |
| status | text | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## planner_milestones

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| goal_id | uuid | NOT NULL | FK → planner_goals.id |
| title | text | NOT NULL |  |
| details | text | NULL |  |
| due_ts | timestamptz | NULL |  |
| horizon | text | NOT NULL |  |
| status | text | NOT NULL |  |
| sequence | int4 | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## planner_weekly_pressure

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| week_start | date | NOT NULL |  |
| week_end | date | NOT NULL |  |
| pressure | jsonb | NOT NULL |  |
| confidence | numeric | NULL |  |
| created_at | timestamptz | NULL |  |

## preference_adjustments

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| domain | text | NOT NULL |  |
| dimension | text | NOT NULL |  |
| old_value | float8 | NULL |  |
| new_value | float8 | NULL |  |
| adjustment | float8 | NULL |  |
| trigger_type | text | NOT NULL |  |
| trigger_id | uuid | NULL |  |
| evidence_text | text | NULL |  |
| old_confidence | float8 | NULL |  |
| new_confidence | float8 | NULL |  |
| created_at | timestamptz | NULL |  |

## preference_domains

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| domain_id | text | NOT NULL | PK |
| display_name | text | NOT NULL |  |
| description | text | NULL |  |
| standard_dimensions | jsonb | NULL |  |
| icon | text | NULL |  |
| created_at | timestamptz | NULL |  |

## preference_events

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int4 | NOT NULL | PK |
| person_id | text | NOT NULL |  |
| domain | text | NOT NULL |  |
| dimension | text | NOT NULL |  |
| value | float8 | NOT NULL |  |
| evidence_type | text | NOT NULL |  |
| source_text | text | NULL |  |
| context | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |

## preference_match_history

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int4 | NOT NULL | PK |
| person_id | text | NOT NULL |  |
| domain | text | NOT NULL |  |
| item_id | text | NULL |  |
| item_description | text | NULL |  |
| predicted_score | float8 | NULL |  |
| actual_feedback | float8 | NULL |  |
| feedback_type | text | NULL |  |
| created_at | timestamptz | NULL |  |

## preference_profiles

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | text | NOT NULL | PK |
| profile_data | jsonb | NOT NULL |  |
| updated_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |

## preference_traits

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| trait_id | text | NOT NULL | PK |
| display_name | text | NOT NULL |  |
| description | text | NULL |  |
| related_domains | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |

## preferences

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → persons.id |
| scope | text | NULL | UNIQUE |
| key | text | NULL | UNIQUE |
| value | jsonb | NULL |  |
| confidence | numeric | NULL |  |
| evidence_ids | _uuid | NULL |  |

## presence_state

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, UNIQUE, FK → persons.id |
| date | date | NOT NULL | PK, UNIQUE |
| summary | text | NULL |  |
| mood_today | text | NULL |  |
| open_actions | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## profiles

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| user_id | uuid | NOT NULL | PK, FK → auth_users.id |
| email | text | NULL | UNIQUE |
| tz | text | NULL |  |
| locale | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |
| allow_bio_data | bool | NULL |  |

## purpose_themes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| theme | text | NOT NULL |  |
| description | text | NULL |  |
| anchors | jsonb | NOT NULL |  |
| momentum | numeric | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## recommendation_feedback

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| recommendation_type | text | NOT NULL |  |
| recommendation_domain | text | NULL |  |
| recommendation_content | jsonb | NOT NULL |  |
| feedback_type | text | NULL |  |
| feedback_text | text | NULL |  |
| rating | float8 | NULL |  |
| was_followed | bool | NULL |  |
| was_reordered | bool | NULL |  |
| time_to_action_seconds | int4 | NULL |  |
| affected_dimensions | jsonb | NULL |  |
| conversation_id | text | NULL |  |
| choice_id | uuid | NULL | FK → user_choices.id |
| created_at | timestamptz | NULL |  |
| acted_at | timestamptz | NULL |  |

## reflection_feedback

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → persons.id |
| reflection_id | int8 | NULL | FK → reflections.id |
| helpful | bool | NULL |  |
| comment | text | NULL |  |
| created_at | timestamptz | NULL |  |

## reflection_inquiry_embeddings

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| turn_id | uuid | NOT NULL | FK → reflection_inquiry_turns.id |
| person_id | uuid | NOT NULL |  |
| content_kind | text | NOT NULL |  |
| content_text | text | NOT NULL |  |
| embedding_vec | vector | NOT NULL |  |
| content_hash | text | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## reflection_inquiry_turns

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| reflection_id | text | NOT NULL |  |
| reflection_kind | text | NULL |  |
| question_text | text | NOT NULL |  |
| answer_text | text | NOT NULL |  |
| answer_mode | text | NOT NULL |  |
| sources_json | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| window_days | int4 | NOT NULL |  |

## reflections

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| user_id | uuid | NOT NULL | FK → persons.id |
| kind | text | NOT NULL |  |
| theme | text | NULL |  |
| content | text | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |
| coherence | numeric | NULL |  |

## registered_agents

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | text | NOT NULL | UNIQUE |
| agent_name | text | NOT NULL |  |
| agent_type | text | NOT NULL |  |
| device_id | text | NOT NULL | UNIQUE |
| agent_version | text | NOT NULL |  |
| protocol_version | text | NULL |  |
| capabilities | jsonb | NULL |  |
| approved_capabilities | jsonb | NULL |  |
| platform | text | NOT NULL |  |
| platform_version | text | NULL |  |
| architecture | text | NULL |  |
| auth_token_hash | text | NOT NULL |  |
| status | text | NULL |  |
| last_heartbeat_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## relationship_state

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| trust_score | numeric | NULL |  |
| attunement_score | numeric | NULL |  |
| emotional_safety | numeric | NULL |  |
| closeness_stage | text | NULL |  |
| preference_profile | jsonb | NOT NULL |  |
| interaction_patterns | jsonb | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## relationships

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → persons.id |
| memory_node_id | uuid | NULL | FK → memory_nodes.id |
| name | text | NOT NULL | UNIQUE |
| relationship_type | text | NOT NULL |  |
| closeness | float8 | NULL |  |
| frequency_target | text | NULL |  |
| last_seen_at | timestamptz | NULL |  |
| last_contact_at | timestamptz | NULL |  |
| last_mentioned_at | timestamptz | NULL |  |
| their_sakhi_id | uuid | NULL |  |
| context | jsonb | NULL |  |
| patterns | jsonb | NULL |  |
| scheduling | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## rhythm_forecasts

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → profiles.user_id |
| forecast_date | date | NULL |  |
| forecast_window | text | NULL |  |
| predicted_energy | float8 | NULL |  |
| predicted_focus | float8 | NULL |  |
| predicted_mood | float8 | NULL |  |
| summary | text | NULL |  |
| recommendations | _text | NULL |  |
| created_at | timestamptz | NULL |  |
| forecast_text | text | NULL |  |
| forecast_vector | vector | NULL |  |
| coherence | float8 | NULL |  |
| predicted_emotion | float8 | NULL |  |
| updated_at | timestamptz | NULL |  |

## rhythm_insights

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → profiles.user_id |
| window_start | date | NULL |  |
| window_end | date | NULL |  |
| pattern_type | text | NULL |  |
| summary | text | NULL |  |
| recommendation | text | NULL |  |
| confidence | float8 | NULL |  |
| created_at | timestamptz | NULL |  |

## rhythm_planner_alignment

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| horizon | text | NOT NULL | PK |
| recommendations | jsonb | NOT NULL |  |
| generated_at | timestamptz | NOT NULL |  |

## rhythm_weekly_rollups

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| week_start | date | NOT NULL |  |
| week_end | date | NOT NULL |  |
| rollup | jsonb | NOT NULL |  |
| confidence | numeric | NULL |  |
| created_at | timestamptz | NULL |  |

## sakhi_connections

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| from_entity_id | uuid | NOT NULL | UNIQUE, FK → sakhi_entities.id |
| to_entity_id | uuid | NOT NULL | UNIQUE, FK → sakhi_entities.id |
| connection_type | text | NOT NULL |  |
| status | text | NOT NULL |  |
| trust_level | text | NULL |  |
| permissions | jsonb | NULL |  |
| relationship_id | uuid | NULL |  |
| custom_label | text | NULL |  |
| notes | text | NULL |  |
| first_interaction_at | timestamptz | NULL |  |
| last_interaction_at | timestamptz | NULL |  |
| interaction_count | int4 | NULL |  |
| connected_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## sakhi_entities

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | text | NOT NULL | UNIQUE |
| entity_type | text | NOT NULL |  |
| display_name | text | NOT NULL |  |
| sakhi_handle | text | NULL | UNIQUE |
| bio | text | NULL |  |
| business_name | text | NULL |  |
| business_type | text | NULL |  |
| business_category | _text | NULL |  |
| location_name | text | NULL |  |
| operating_hours | jsonb | NULL |  |
| capabilities | jsonb | NULL |  |
| share_availability | bool | NULL |  |
| availability_detail | text | NULL |  |
| auto_accept_from | _text | NULL |  |
| require_confirmation | bool | NULL |  |
| auto_respond_inquiries | bool | NULL |  |
| discoverable | bool | NULL |  |
| verified | bool | NULL |  |
| active | bool | NULL |  |
| last_active_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## sakhi_invite_links

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| code | text | NOT NULL | UNIQUE |
| custom_message | text | NULL |  |
| max_uses | int4 | NULL |  |
| uses_remaining | int4 | NULL |  |
| default_trust_level | text | NULL |  |
| expires_at | timestamptz | NULL |  |
| active | bool | NULL |  |
| created_at | timestamptz | NULL |  |

## sakhi_offerings

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| offering_type | text | NOT NULL |  |
| name | text | NOT NULL |  |
| description | text | NULL |  |
| category | _text | NULL |  |
| tags | _text | NULL |  |
| pricing | jsonb | NULL |  |
| available | bool | NULL |  |
| quantity_available | int4 | NULL |  |
| availability_schedule | jsonb | NULL |  |
| requires_booking | bool | NULL |  |
| duration_minutes | int4 | NULL |  |
| booking_advance_hours | int4 | NULL |  |
| images | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## sakhi_registry

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| sakhi_id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE |
| display_name | text | NOT NULL |  |
| avatar_url | text | NULL |  |
| endpoint_url | text | NULL |  |
| public_key | text | NULL |  |
| mesh_enabled | bool | NULL |  |
| capabilities | jsonb | NULL |  |
| discoverable | bool | NULL |  |
| share_availability | bool | NULL |  |
| share_preferences | bool | NULL |  |
| status | text | NULL |  |
| last_seen_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## sakhi_reviews

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| reviewer_entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| reviewed_entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| transaction_id | uuid | NULL | FK → sakhi_transactions.id |
| offering_id | uuid | NULL | FK → sakhi_offerings.id |
| thread_id | uuid | NULL | FK → coordination_threads.id |
| rating | float8 | NOT NULL |  |
| title | text | NULL |  |
| content | text | NULL |  |
| aspect_ratings | jsonb | NULL |  |
| response | text | NULL |  |
| response_at | timestamptz | NULL |  |
| verified_interaction | bool | NULL |  |
| status | text | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## sakhi_transactions

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| buyer_entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| seller_entity_id | uuid | NOT NULL | FK → sakhi_entities.id |
| offering_id | uuid | NULL | FK → sakhi_offerings.id |
| description | text | NOT NULL |  |
| quantity | int4 | NULL |  |
| unit_price | numeric | NULL |  |
| total_amount | numeric | NULL |  |
| currency | text | NULL |  |
| status | text | NOT NULL |  |
| thread_id | uuid | NULL | FK → coordination_threads.id |
| fulfillment | jsonb | NULL |  |
| confirmed_at | timestamptz | NULL |  |
| paid_at | timestamptz | NULL |  |
| fulfilled_at | timestamptz | NULL |  |
| completed_at | timestamptz | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## salient_memories

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| user_id | uuid | NOT NULL |  |
| session_id | uuid | NULL | FK → conversation_sessions.id |
| kind | text | NOT NULL |  |
| key | text | NOT NULL |  |
| value | jsonb | NOT NULL |  |
| source_turn_id | uuid | NULL | FK → conversation_turns.id |
| salience | float8 | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## scheduling_preferences

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → persons.id |
| preferred_times | jsonb | NULL |  |
| avoid_times | jsonb | NULL |  |
| buffer_minutes | int4 | NULL |  |
| max_events_per_day | int4 | NULL |  |
| preferred_durations | jsonb | NULL |  |
| location_preferences | jsonb | NULL |  |
| dining_preferences | jsonb | NULL |  |
| energy_preferences | jsonb | NULL |  |
| communication_preferences | jsonb | NULL |  |
| created_at | timestamptz | NULL |  |
| updated_at | timestamptz | NULL |  |

## scheduling_requests

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| original_request | text | NOT NULL |  |
| parsed_intent | jsonb | NOT NULL |  |
| related_person_ids | _uuid | NULL |  |
| proposed_times | jsonb | NULL |  |
| selected_option | int4 | NULL |  |
| status | text | NOT NULL |  |
| resulting_event_id | uuid | NULL |  |
| resolved_at | timestamptz | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## self_report_body

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| energy_level | float8 | NULL |  |
| fatigue_level | float8 | NULL |  |
| tension_neck_shoulders | float8 | NULL |  |
| tension_back | float8 | NULL |  |
| tension_jaw | float8 | NULL |  |
| tension_other | text | NULL |  |
| hunger_level | float8 | NULL |  |
| digestion_quality | text | NULL |  |
| bloating | bool | NULL |  |
| elimination_regular | bool | NULL |  |
| feeling_cold | bool | NULL |  |
| feeling_hot | bool | NULL |  |
| hydration_level | float8 | NULL |  |
| breath_quality | text | NULL |  |
| cravings | _text | NULL |  |
| notes | text | NULL |  |
| recorded_at | timestamptz | NULL |  |

## sensory_preferences

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK |
| temperature | jsonb | NULL |  |
| texture | jsonb | NULL |  |
| spice | jsonb | NULL |  |
| flavor | jsonb | NULL |  |
| visual | jsonb | NULL |  |
| ambiance | jsonb | NULL |  |
| portion | jsonb | NULL |  |
| service | jsonb | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## session_continuity

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → persons.id |
| last_emotion | text | NULL |  |
| last_interaction_ts | timestamptz | NULL |  |
| engagement_level | numeric | NULL |  |
| reflection_pending | bool | NULL |  |
| clarity_level | float8 | NULL |  |

## session_summaries

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| session_id | uuid | NOT NULL | PK, FK → conversation_sessions.id |
| summary | text | NOT NULL |  |
| last_updated | timestamptz | NOT NULL |  |
| turn_count_at_summary | int4 | NULL |  |

## shared_availability

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| entity_id | uuid | NOT NULL | UNIQUE, FK → sakhi_entities.id |
| availability_type | text | NULL | UNIQUE |
| offering_id | uuid | NULL | FK → sakhi_offerings.id |
| valid_from | timestamptz | NOT NULL | UNIQUE |
| valid_until | timestamptz | NOT NULL |  |
| busy_free | jsonb | NOT NULL |  |
| windows | jsonb | NULL |  |
| detailed | jsonb | NULL |  |
| computed_at | timestamptz | NULL |  |

## soul_values

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| value_name | text | NOT NULL |  |
| description | text | NULL |  |
| confidence | numeric | NOT NULL |  |
| anchors | jsonb | NOT NULL |  |
| evidence | jsonb | NOT NULL |  |
| created_at | timestamptz | NOT NULL |  |

## surfaced_aspects

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| user_id | uuid | NOT NULL | PK |
| key | text | NOT NULL | PK |
| last_surfaced_at | timestamptz | NOT NULL |  |

## symptom_episodes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL |  |
| symptom | text | NOT NULL |  |
| occurred_at | timestamptz | NOT NULL |  |
| duration_hours | int4 | NULL |  |
| likely_cause | text | NULL |  |
| what_helped | jsonb | NULL |  |
| recovery_time_hours | int4 | NULL |  |
| notes | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |

## symptom_log

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| symptom_type | text | NOT NULL |  |
| severity | float8 | NULL |  |
| occurred_at | timestamptz | NULL |  |
| resolution_time | timestamptz | NULL |  |
| interventions_tried | jsonb | NULL |  |
| what_helped | jsonb | NULL |  |
| what_didnt_help | jsonb | NULL |  |
| resolution_summary | text | NULL |  |
| related_dosha | text | NULL |  |
| created_at | timestamptz | NULL |  |
| symptom_name | text | NULL |  |
| time_of_day | text | NULL |  |
| likely_dosha | text | NULL |  |
| source | text | NULL |  |
| related_entry_id | text | NULL |  |
| source_text | text | NULL |  |

## system_events

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | int8 | NOT NULL | PK |
| ts | timestamptz | NULL |  |
| person_id | uuid | NULL |  |
| layer | text | NULL |  |
| event | text | NULL |  |
| payload | jsonb | NULL |  |

## system_tempo

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| phase | text | NULL |  |
| tempo | float8 | NULL |  |
| coherence | float8 | NULL |  |
| updated_at | timestamptz | NULL |  |

## task_dependencies

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| task_id | uuid | NOT NULL | PK, FK → tasks.id |
| depends_on_task_id | uuid | NOT NULL | PK, FK → tasks.id |
| hard | bool | NOT NULL |  |

## task_routing_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| task_id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → profiles.user_id |
| category | text | NOT NULL |  |
| recommended_window | text | NULL |  |
| reason | text | NULL |  |
| forecast_snapshot | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## tasks

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| user_id | uuid | NOT NULL | FK → profiles.user_id |
| title | text | NOT NULL |  |
| status | text | NOT NULL |  |
| due_at | timestamptz | NULL |  |
| priority | int4 | NOT NULL |  |
| tags | _text | NULL |  |
| notes | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |
| parent_task_id | uuid | NULL | FK → tasks.id |
| order_index | int4 | NOT NULL |  |
| estimated_min | int4 | NULL |  |
| value_score | int4 | NULL |  |
| hard_block | bool | NOT NULL |  |
| description | text | NULL |  |
| canonical_intent | text | NULL |  |
| inferred_time_horizon | text | NULL |  |
| energy_cost | float8 | NULL |  |
| emotional_fit | text | NULL |  |
| auto_priority | float8 | NULL |  |
| anchor_goal_id | uuid | NULL | FK → planner_goals.id |
| routing_state | jsonb | NULL |  |

## theme_rhythm_links

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → profiles.user_id |
| theme | text | NOT NULL |  |
| correlation | float8 | NULL |  |
| clarity_trend | float8 | NULL |  |
| energy_trend | float8 | NULL |  |
| samples | int4 | NULL |  |
| updated_at | timestamptz | NULL |  |

## theme_states

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NULL | FK → profiles.user_id |
| theme | text | NOT NULL |  |
| rhythm_state | jsonb | NULL |  |
| emotional_state | jsonb | NULL |  |
| clarity_score | float8 | NULL |  |
| updated_at | timestamptz | NULL |  |

## themes

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| name | text | NULL |  |
| description | text | NULL |  |
| scope | text | NULL |  |
| embed | vector | NULL |  |
| signals | jsonb | NULL |  |
| trend | jsonb | NULL |  |
| embed_vec | vector | NULL |  |

## thread_continuity_markers

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | UNIQUE, FK → profiles.user_id |
| thread_id | uuid | NOT NULL | UNIQUE |
| continuity_hint | text | NULL |  |
| persona_stability | jsonb | NOT NULL |  |
| last_turn_id | uuid | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## user_choices

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | uuid | NOT NULL | FK → persons.id |
| choice_context | text | NOT NULL |  |
| options_presented | jsonb | NOT NULL |  |
| option_count | int4 | NULL |  |
| chosen_option | jsonb | NULL |  |
| chosen_index | int4 | NULL |  |
| inferred_reasons | jsonb | NULL |  |
| conversation_id | text | NULL |  |
| recommendation_id | text | NULL |  |
| created_at | timestamptz | NULL |  |

## users

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| email | text | NOT NULL | UNIQUE |
| full_name | text | NULL |  |
| password_hash | text | NULL |  |
| created_at | timestamptz | NOT NULL |  |
| updated_at | timestamptz | NOT NULL |  |

## vision_memory

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | text | NOT NULL |  |
| media_id | uuid | NULL | FK → media_attachments.id |
| memory_type | text | NOT NULL |  |
| subject | text | NOT NULL |  |
| learned_facts | jsonb | NULL |  |
| embedding | vector | NULL |  |
| source_description | text | NULL |  |
| confidence | float8 | NULL |  |
| first_seen_at | timestamptz | NULL |  |
| last_confirmed_at | timestamptz | NULL |  |
| times_seen | int4 | NULL |  |
| created_at | timestamptz | NULL |  |

## visual_context

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | PK |
| person_id | text | NOT NULL | UNIQUE |
| session_id | text | NOT NULL | UNIQUE |
| active_media | jsonb | NULL |  |
| visual_summary | text | NULL |  |
| objects_mentioned | jsonb | NULL |  |
| people_mentioned | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |

## wellness_state_cache

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| person_id | uuid | NOT NULL | PK, FK → profiles.user_id |
| body | jsonb | NULL |  |
| mind | jsonb | NULL |  |
| emotion | jsonb | NULL |  |
| energy | jsonb | NULL |  |
| updated_at | timestamptz | NULL |  |
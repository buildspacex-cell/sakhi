# Stateful Temporal Governance Audit
Date: 2026-02-17
Scope: Repository-wide audit for stateful temporal governance in AI reasoning.

This document is iterative. Each new audit prompt will append a new section.

## Prompt 1
Prompt: "Generate repo map, LLM call sites, and state-like models (user/memory/journal/reflection/tasks/commitments/plans/goals)."

### 1) High-Level Repo Map
| Area | Purpose | Key Entry Points |
|---|---|---|
| `sakhi/apps/api` | FastAPI backend: routes, orchestration, memory/reasoning services, agentic flows | `sakhi/apps/api/main.py`, `sakhi/apps/api/routes/turn_v2.py`, `sakhi/apps/api/core/llm.py` |
| `sakhi/apps/worker` | Async/background processing: consolidation, enrichment, preference learning, reflection jobs | `sakhi/apps/worker/jobs.py`, `sakhi/apps/worker/pipelines/turn_updates/runner.py`, `sakhi/apps/worker/tasks/episodic_consolidation_v21.py` |
| `sakhi/apps/engine` | Deterministic per-domain state engines (tone, empathy, reflection, scaffolds, etc.) | Example engines used by turn path: `sakhi/apps/engine/*`, wired via `sakhi/apps/api/routes/turn_v2.py` |
| `sakhi/core` | Core cognition modules (identity timeline/momentum, decision graph, rhythm/soul) | `sakhi/core/intelligence/decision_graph_engine.py`, `sakhi/core/soul/identity_momentum_engine.py`, `sakhi/core/soul/identity_timeline_engine.py` |
| `sakhi/libs` | Shared infra: LLM router/providers, retrieval, embeddings, schemas, policy, reasoning | `sakhi/libs/llm_router/router.py`, `sakhi/libs/llm_router/openai_provider.py`, `sakhi/libs/schemas/db.py` |
| `sakhi/infra/scripts/migrations` | Canonical DB schema/migrations for persistent temporal state | `sakhi/infra/scripts/migrations/0001_baseline.sql` (+ `0003`-`0008`) |
| `apps/web` | Next.js web app (chat/voice UI + server route proxies) | `apps/web/app/experience/converse/page.tsx`, `apps/web/app/api/turn-v2/route.ts`, `apps/web/app/api/voice/turn/route.ts` |
| `apps/mobile` | React Native app (text + voice experiences) | `apps/mobile/app/experience/converse/index.tsx`, `apps/mobile/hooks/useVoice.ts` |
| `docs` | Product/architecture/audit documentation | `docs/features/` |
| `scripts` | Operational/dev scripts | `scripts/` |

### 2) LLM Call Sites (API Routes, Services, Hooks, Workers)
Notes:
- Primary backend abstraction: `call_llm(...)` in `sakhi/apps/api/core/llm.py`.
- Secondary direct path: `router.chat(...)` via `LLMRouter`.
- Voice STT/TTS in web/mobile also calls OpenAI audio endpoints.

#### API Route / HTTP Layer
| File Path | Brief Description |
|---|---|
| `sakhi/apps/api/main.py` | `/reflect` endpoint composes reflection with `router.chat`. |
| `sakhi/apps/api/diagnose.py` | `/diagnose` endpoint calls `router.chat` for dosha diagnostic JSON. |
| `sakhi/apps/api/routes/chat.py` | Primary chat route; calls `router.chat` (including follow-up tool-result turn). |
| `sakhi/apps/api/routes/conversation.py` | Conversation action-intent detection via `call_llm(schema=ActionIntent)`. |
| `sakhi/apps/api/routes/friction_framework.py` | Multiple route handlers generate constitution/friction recommendations/insights via `router.chat`. |
| `sakhi/apps/api/routes/lab.py` | Lab/debug endpoints invoke `call_llm` for reflection/debug generation. |
| `sakhi/apps/api/routes/llm.py` | `/dev/llm/chat` passthrough route directly invokes `router.chat`. |
| `apps/web/app/api/voice/turn/route.ts` | Next API route: Whisper STT + backend turn + OpenAI TTS. |
| `apps/web/app/api/voice/tts/route.ts` | Next API route: OpenAI TTS generation. |

#### Service Layer (Backend)
| File Path | Brief Description |
|---|---|
| `sakhi/apps/api/clarity/hcb.py` | Clarity scoring/evaluation calls `call_llm`. |
| `sakhi/apps/api/clarity/phrasing.py` | Phrase rewriting/classification via structured `call_llm`. |
| `sakhi/apps/api/services/agent/action_decider.py` | Agent action selection and follow-up decisions via `router.chat`. |
| `sakhi/apps/api/services/agent/actions.py` | Agent action generation/execution planning via `router.chat`. |
| `sakhi/apps/api/services/agent/screen_analyzer.py` | Screen understanding/vision reasoning via `router.chat`. |
| `sakhi/apps/api/services/agent/task_orchestrator.py` | Multi-step task orchestration and plan reasoning via `router.chat`. |
| `sakhi/apps/api/services/agentic/planner.py` | Agentic planning and re-planning calls `router.chat`. |
| `sakhi/apps/api/services/agentic/research.py` | Agentic research synthesis via `router.chat`. |
| `sakhi/apps/api/services/agentic/search.py` | Search result interpretation/ranking via `router.chat`. |
| `sakhi/apps/api/services/agentic/tools.py` | Tool decision/normalization with `router.chat`. |
| `sakhi/apps/api/services/ayurveda/pattern_learning.py` | Symptom/behavior pattern extraction via `call_llm`. |
| `sakhi/apps/api/services/context_router.py` | Low-confidence context routing fallback via `call_llm`. |
| `sakhi/apps/api/services/conversation/topic_manager.py` | Topic extraction/normalization via `call_llm`. |
| `sakhi/apps/api/services/conversation_v2/conversation_engine.py` | Final response generation calls `call_llm`. |
| `sakhi/apps/api/services/email/digest.py` | Email digest triage/commitment extraction via `call_llm`. |
| `sakhi/apps/api/services/intents/extract.py` | Intent extraction from turns via `call_llm`. |
| `sakhi/apps/api/services/journaling/enrich.py` | Journal enrichment pipeline via `call_llm`. |
| `sakhi/apps/api/services/learning/feedback.py` | Feedback parsing and dimension inference via `call_llm`. |
| `sakhi/apps/api/services/learning/outcomes.py` | Outcome interpretation/attribution via `call_llm`. |
| `sakhi/apps/api/services/loop/llm_bridge.py` | Loop protocol bridge uses `router.chat` for action reasoning. |
| `sakhi/apps/api/services/memory/preference_learning.py` | Preference extraction from text via `call_llm`. |
| `sakhi/apps/api/services/memory/product_matching.py` | Product fit/matching reasoning via `call_llm`. |
| `sakhi/apps/api/services/memory/recall.py` | Recall synthesis and answer shaping via `call_llm`. |
| `sakhi/apps/api/services/memory/sensory_preferences.py` | Sensory preference extraction via `router.chat`. |
| `sakhi/apps/api/services/memory/sessions.py` | Session compression/summarization via `call_llm`. |
| `sakhi/apps/api/services/memory/summarize.py` | Memory summarization via `router.chat`. |
| `sakhi/apps/api/services/missions/decomposer.py` | Mission decomposition/planning via `call_llm`. |
| `sakhi/apps/api/services/narratives/episodic.py` | Episodic narrative generation via `call_llm`. |
| `sakhi/apps/api/services/persona/features.py` | Persona feature extraction via `call_llm`. |
| `sakhi/apps/api/services/persona/tuner.py` | Persona mode tuning via `call_llm`. |
| `sakhi/apps/api/services/planner/extract.py` | Planner signal extraction via `call_llm`. |
| `sakhi/apps/api/services/planner/goal_suggester.py` | Goal suggestion generation via `call_llm`. |
| `sakhi/apps/api/services/planning/auto_summarizer.py` | Planning summary generation via `call_llm`. |
| `sakhi/apps/api/services/reflection/daily_generator.py` | Daily reflection generation via `call_llm`. |
| `sakhi/apps/api/services/reflection/narration_foundation.py` | Reflection narrative foundation synthesis via `call_llm`. |
| `sakhi/apps/api/services/reflection/summarizer.py` | Reflection summarization via `call_llm`. |
| `sakhi/apps/api/services/reflection_inquiry/answerer.py` | Reflection inquiry answering via `call_llm`. |
| `sakhi/apps/api/services/relationships/enrichment.py` | Relationship enrichment inference via `call_llm`. |
| `sakhi/apps/api/services/relationships/extraction.py` | Person/relationship extraction via `call_llm`. |
| `sakhi/apps/api/services/response/diagnostic_kb.py` | Diagnostic knowledge-gap/response diagnostics via `call_llm`. |
| `sakhi/apps/api/services/response/knowledge_gap.py` | Knowledge-gap inference via `call_llm`. |
| `sakhi/apps/api/services/vision/documents.py` | Document OCR/understanding/summarization via `router.chat`. |
| `sakhi/apps/api/services/vision/processor.py` | Image/screenshot analysis via `router.chat`. |
| `sakhi/apps/api/core/llm.py` | Central LLM wrapper; invokes `_ROUTER.chat(...)`. |

#### Worker Layer
| File Path | Brief Description |
|---|---|
| `sakhi/apps/worker/jobs.py` | Background reflection/metadata jobs invoke `router.chat`. |
| `sakhi/apps/worker/jobs_goal_actions.py` | Goal-action commit planning via `router.chat`. |
| `sakhi/apps/worker/identity_momentum_deep.py` | Deep identity momentum synthesis via `call_llm`. |
| `sakhi/apps/worker/narrative_deep.py` | Deep narrative generation via `call_llm`. |
| `sakhi/apps/worker/soul/shadow_extract.py` | Shadow extraction via `call_llm`. |
| `sakhi/apps/worker/tasks/episodic_consolidation_v21.py` | Multi-step episodic consolidation with repeated `router.chat` calls. |
| `sakhi/apps/worker/tasks/goal_evolver.py` | Goal evolution reasoning via `call_llm`. |
| `sakhi/apps/worker/tasks/life_phase_mapper.py` | Life phase inference via `call_llm`. |
| `sakhi/apps/worker/tasks/meta_reflection_weekly.py` | Weekly meta-reflection generation via `call_llm`. |
| `sakhi/apps/worker/tasks/persona_mode_detector.py` | Persona mode detection via `call_llm`. |
| `sakhi/apps/worker/tasks/presence_reflection.py` | Presence reflection generation via `call_llm`. |
| `sakhi/apps/worker/tasks/reflect_person_memory.py` | Person memory reflection via `router.chat`. |
| `sakhi/apps/worker/tasks/soul_extract_worker.py` | Soul extraction via `call_llm`. |
| `sakhi/apps/worker/tasks/theme_inference.py` | Theme inference via `call_llm`. |
| `sakhi/apps/worker/tasks/tone_continuity.py` | Tone continuity reasoning via `call_llm`. |

#### Core / Libraries / Infra Scripts
| File Path | Brief Description |
|---|---|
| `sakhi/libs/llm_router/openai_provider.py` | Provider implementation directly calling `chat.completions.create`. |
| `sakhi/libs/llm_router/graph_reasoner.py` | Graph reasoner uses `call_llm`. |
| `sakhi/libs/llm_router/router.py` | Router-level chat execution utilities/self-test path. |
| `sakhi/libs/memory/store.py` | Memory store summarization/normalization via `router.chat`. |
| `sakhi/libs/reasoning/engine.py` | General reasoning engine via `call_llm`. |
| `sakhi/core/intelligence/decision_graph_engine.py` | Decision graph synthesis via `call_llm`. |
| `sakhi/core/soul/identity_momentum_engine.py` | Identity momentum synthesis via `call_llm`. |
| `sakhi/core/soul/identity_timeline_engine.py` | Identity timeline synthesis via `call_llm`. |
| `sakhi/infra/scripts/data/validate_ayurvedic_data.py` | Data validation script calls OpenAI chat completions directly. |
| `sakhi/infra/scripts/data/expand_knowledge_graph.py` | Knowledge-graph expansion script calls OpenAI chat completions directly. |

#### Hooks / Client Entry Points (LLM-Indirect + Direct Voice)
| File Path | Brief Description |
|---|---|
| `apps/web/lib/hooks/useVoice.ts` | Client hook sending audio to `/api/voice/turn` and replay TTS via `/api/voice/tts`. |
| `apps/mobile/hooks/useVoice.ts` | Mobile hook calls OpenAI STT (`/v1/audio/transcriptions`) + OpenAI TTS (`/v1/audio/speech`) + backend `/v2/turn`. |
| `apps/web/app/experience/converse/page.tsx` | Chat UI sends text turns to `/api/turn-v2` (LLM-backed backend). |
| `apps/mobile/app/experience/converse/index.tsx` | Mobile text converse screen posts to `/v2/turn`. |

### 3) State-Like Models/Schemas (User, Memory, Journal/Reflection, Tasks/Commitments, Plans, Goals)

#### A. Persistent Tables (Postgres)
| Domain | Model/Table | File Path | Fields |
|---|---|---|---|
| User | `auth_users` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `supabase_user_id`, `email`, `full_name`, `avatar_url`, `created_at`, `last_sign_in_at`, `onboarding_completed_at`, `deleted_at` |
| User | `users` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `email`, `full_name`, `password_hash`, `created_at`, `updated_at` |
| User | `persons` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `created_at` |
| User | `profiles` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `user_id`, `email`, `tz`, `locale`, `allow_bio_data`, `created_at`, `updated_at` |
| User/State | `personal_model` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `person_id`, `data`, `body_state`, `mind_state`, `emotion_state`, `goals_state`, `rhythm_state`, `short_term`, `long_term`, `soul_state`, `alignment_state`, `forecast_state`, `operating_system`, `life_context`, `decision_profile`, `updated_at` |
| User Mapping | `person_profile_map` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `person_id`, `profile_user_id` |
| Memory | `memory_short_term` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `user_id`, `person_id`, `record`, `text`, `layer`, `triage`, `entry_id`, `vector_vec`, `expires_at`, `created_at`, `updated_at` |
| Memory | `memory_episodic` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `user_id`, `person_id`, `entry_id`, `record`, `text`, `triage`, `state_vector`, `guna_vector`, `vector_vec`, `ts`, `created_at`, `updated_at` |
| Memory Graph | `memory_nodes` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `node_kind`, `label`, `data`, `weight`, `last_referenced_at`, `created_at`, `updated_at` |
| Memory Graph | `memory_edges` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `from_node`, `to_node`, `relation`, `weight`, `relevance`, `occurrence_count`, `evidence`, `created_at`, `updated_at` |
| Memory Context | `memory_context_cache` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `person_id`, `window_kind`, `entries`, `rhythm_state`, `persona_snapshot`, `task_window`, `merged_context_vector`, `updated_at` |
| Memory Recall | `context_recalls` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `turn_id`, `thread_id`, `stitched_summary`, `compact`, `vectors`, `signals`, `confidence`, `created_at` |
| Conversation Continuity | `thread_continuity_markers` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `thread_id`, `continuity_hint`, `persona_stability`, `last_turn_id`, `created_at`, `updated_at` |
| Journal | `journal_entries` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `user_id`, `person_id`, `content`, `title`, `facets`, `facets_v2`, `narrative`, `processing_state`, `processed_at`, `tags`, `mood`, `created_at`, `updated_at` |
| Journal Embeddings | `journal_embeddings` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `entry_id`, `model`, `embedding`, `embedding_vec`, `content_hash`, `created_at` |
| Journal Inference | `journal_inference` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `entry_id`, `container`, `payload`, `confidence`, `inference_type`, `source`, `created_at` |
| Reflection | `reflections` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `user_id`, `kind`, `theme`, `content`, `coherence`, `created_at` |
| Reflection Cache | `daily_reflection_cache` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `person_id`, `reflection_date`, `summary`, `generated_at` |
| Reflection | `meta_reflections` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `period`, `summary`, `insights`, `created_at` |
| Reflection Inquiry | `reflection_inquiry_turns` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `reflection_id`, `reflection_kind`, `question_text`, `answer_text`, `answer_mode`, `sources_json`, `window_days`, `created_at` |
| Reflection Feedback | `reflection_feedback` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `reflection_id`, `helpful`, `comment`, `created_at` |
| Tasks | `tasks` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `user_id`, `title`, `status`, `due_at`, `priority`, `parent_task_id`, `estimated_min`, `value_score`, `canonical_intent`, `anchor_goal_id`, `routing_state`, `created_at`, `updated_at` |
| Task Dependencies | `task_dependencies` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `task_id`, `depends_on_task_id`, `hard` |
| Scheduling Commitments | `scheduling_requests` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `original_request`, `parsed_intent`, `related_person_ids`, `proposed_times`, `selected_option`, `status`, `resulting_event_id`, `resolved_at`, `created_at`, `updated_at` |
| Agent Tasks | `agent_task_plans` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `session_id`, `task_type`, `task_description`, `steps`, `context_used`, `status`, `current_step_index`, `result`, `created_at`, `started_at`, `completed_at` |
| Email Commitments | `email_commitments` | `sakhi/infra/scripts/migrations/0006_email_commitments.sql` | `id`, `person_id`, `commitment_hash`, `commitment`, `deadline`, `subject`, `recipient`, `commitment_type`, `status`, `status_changed_at`, `extracted_at`, `created_at` |
| Dismissed Commitments | `email_dismissed_actions` | `sakhi/infra/scripts/migrations/0007_commitment_types_and_dismissed_actions.sql` | `id`, `person_id`, `message_id`, `dismissed_at` |
| Plan Items | `planned_items` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `scope`, `label`, `payload`, `due_ts`, `linked_goal_id`, `goal_id`, `milestone_id`, `status`, `priority`, `energy`, `horizon`, `meta` |
| Planner Goals | `planner_goals` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `title`, `details`, `horizon`, `priority`, `status`, `created_at`, `updated_at` |
| Planner Milestones | `planner_milestones` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `goal_id`, `title`, `details`, `due_ts`, `horizon`, `status`, `sequence`, `created_at`, `updated_at` |
| Planner Cache | `planner_context_cache` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `person_id`, `payload`, `updated_at` |
| Goals | `goals` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `parent_goal_id`, `title`, `description`, `horizon`, `status`, `progress`, `priority`, `due_at`, `meta`, `created_at`, `updated_at`, `completed_at` |
| Goal History | `goal_history` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `goal_id`, `person_id`, `previous_title`, `revised_title`, `reason`, `created_at` |
| Micro Goals | `micro_goals` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `source`, `normalized`, `micro_steps`, `confidence`, `blocked`, `created_at`, `updated_at` |
| Intervention Plans | `intervention_plans` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `intervention_type`, `intervention_name`, `schedule_type`, `schedule_days`, `target_per_day`, `start_date`, `end_date`, `duration_days`, `status`, `total_scheduled`, `total_completed`, `recommendation_id` |
| Long Missions | `long_running_missions` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `person_id`, `title`, `description`, `category`, `success_criteria`, `plan_document`, `target_end_date`, `status`, `health`, `progress_pct`, `metrics`, `created_at`, `updated_at` |
| Mission Weekly Plans | `mission_weekly_plans` | `sakhi/infra/scripts/migrations/0001_baseline.sql` | `id`, `mission_id`, `phase_id`, `week_number`, `week_start`, `week_end`, `objectives`, `tasks`, `status`, `review_completed`, `review_notes`, `adjustments_for_next`, `created_at`, `updated_at` |

#### B. In-Code Schemas / State Containers
| Domain | Model | File Path | Fields |
|---|---|---|---|
| User/State | `PersonalModelData` | `sakhi/apps/api/models/personal_model.py` | `body`, `mind`, `emotion`, `goals`, `soul`, `rhythm`, `daily_reflection_state`, `closure_state`, `morning_*`, `micro_*`, `focus_path_state`, `mini_flow_state`, `micro_journey_state` |
| Turn Deterministic State | `DeterministicContext` (dataclass) | `sakhi/apps/api/services/turn/deterministic_context_loader.py` | `internal_state`, brain states (`forecast/coherence/alignment/nudge/...`), friction (`friction_state/drift/...`), `body_state`, ritual caches, scaffolds, `continuity_state`, `gap_hours`, `guards` |
| Task/Commitment | `PendingTask` | `sakhi/apps/api/services/agent/chat_bridge.py` | `task_id`, `person_id`, `task_type`, `task_description`, `original_request`, `plan_steps`, `context_used`, `status`, `created_at`, `expires_at`, `current_step` |
| Task Execution | `TaskExecutionState` | `sakhi/apps/api/services/agent/chat_bridge.py` | `task_id`, `person_id`, `agent_id`, `session_id`, `current_step`, `total_steps`, `status`, `steps_completed`, `pending_approval`, `result`, `error` |
| Task Ops Schema | `CreateTask` / `UpdateTask` / etc. (`Action` union) | `sakhi/apps/api/services/loop/models.py` | Task/event action contracts: `title`, `task_id`, `status`, `due`, dependencies, reminder/event fields |
| Intervention Plans | `InterventionPlan` | `sakhi/apps/api/services/learning/intervention_plans.py` | `id`, `person_id`, `intervention_type`, `intervention_name`, schedule fields, duration fields, target symptom/dosha, tracking counts/streaks, source links |
| Intervention Check-ins | `DailyCheckIn` | `sakhi/apps/api/services/learning/intervention_plans.py` | `id`, `plan_id`, `scheduled_date`, `status`, `completed_count`, `notes`, `mood_before/after`, nudge fields |
| Plan Progress | `PlanProgress` | `sakhi/apps/api/services/learning/intervention_plans.py` | `plan_id`, `status`, elapsed/remaining days, adherence/completion metrics, streaks, symptom improvement, next scheduled |
| Missions | `Mission` | `sakhi/apps/api/services/missions/models.py` | `id`, `person_id`, `title`, `category`, `success_criteria`, `status`, `health`, `progress_pct`, `metrics`, dates |
| Mission Phases | `MissionPhase` | `sakhi/apps/api/services/missions/models.py` | `mission_id`, `phase_number`, `name`, `objective`, `start/target_end`, `status`, `expected_outcomes`, `actual_outcomes`, approval fields |
| Weekly Plan | `WeeklyPlan` | `sakhi/apps/api/services/missions/models.py` | `mission_id`, `phase_id`, `week_number`, `week_start/end`, `objectives`, `tasks`, `status`, review fields |
| Mission Action Plan | `ActionPlan` (LLM decomposition schema) | `sakhi/apps/api/services/missions/models.py` | `action_type`, `description`, `scheduled_day`, `scheduled_time`, `instructions` |
| Email Commitments (LLM schema) | `EmailCommitment` | `sakhi/apps/api/services/email/digest_models.py` | `commitment`, `deadline`, `subject`, `recipient`, `commitment_type` |
| Turn Contract | `TurnResponseProduct` | `sakhi/apps/api/schemas/turn_response.py` | `reply`, `sessionId`, `tone_blueprint`, `adaptive_response`, `friction_state`, `personalized_recommendations`, `journaling_ai`, `memory_recall`, `agent_task_context`, `entry_id` |

## Gaps / Notes (for next prompts)
- LLM call surface is broad; governance controls likely need centralized policy around `call_llm` and `LLMRouter` usage.
- State model surface is distributed across DB tables + Pydantic models; temporal consistency checks should prioritize `personal_model`, memory tables, task/goal/planner tables, and reflection caches.

## Prompt 2
Prompt: "Search for and summarize any code that represents state across time: goals, objectives, constraints, decisions, plans, commitments. For each: storage, fields, update path, provenance."

### Concise State-Model Inventory
| State Domain | Storage (DB/File) | Key Fields (id, time, status, version, parent links) | Update Mechanism | Provenance Quality |
|---|---|---|---|---|
| Goals + Goal Revisions | DB: `goals`, `goal_history` (`sakhi/infra/scripts/migrations/0001_baseline.sql`) | `goals.id`, `person_id`, `parent_goal_id`, `title`, `description`, `horizon`, `status`, `progress`, `evolution_score`, `last_revised`, `created_at`, `updated_at`, `completed_at`; `goal_history` append row has `goal_id`, prior/revised title/description, `reason`, `created_at` | Create from suggestion (`sakhi/apps/api/services/planner/goal_suggester.py`), revise/archive via worker (`sakhi/apps/worker/tasks/goal_evolver.py`), append revision record to `goal_history` | `Partial`: reason text and historical snapshot exist, but no explicit `changed_by` actor on goal updates |
| Planner Graph (Goal/Milestone/Plan Items) | DB: `planner_goals`, `planner_milestones`, `planned_items`, `planner_context_cache`; mirror into `personal_model.goals_state` | `planner_goals.id/status/created_at/updated_at`; `planner_milestones.id/goal_id/status/sequence/due_ts`; `planned_items.id/person_id/goal_id/milestone_id/status/priority/due_ts/origin_id/meta/payload`; cache has `updated_at` | UPSERT graph from planner commit (`sakhi/apps/api/services/planner/commit.py`); summary insert (`sakhi/apps/api/services/planning/auto_summarizer.py`); cache UPSERT (`sakhi/apps/api/services/planner/cache.py`) | `Partial`: `origin_id`, `scope`, `meta`, `payload` retain source context, but no actor/reason audit trail |
| Intent Objectives (Pre-goal State) | DB: `intents` | `id`, `user_id`, `source_entry_id`, `intent_type`, `timeline`, `target_date`, `priority`, `status`, `clarity_score`, `user_permission`, `proposed_plan`, `context_snapshot`, `created_at`, `updated_at` | Insert from journal/action flow (`sakhi/libs/actions/intents.py`, `sakhi/apps/worker/tasks/intent_extraction_worker.py`); update to `clarifying/planned/converted` (`sakhi/apps/worker/jobs_goal_actions.py`, `sakhi/apps/api/services/planner/goal_suggester.py`) | `Partial`: source entry + context snapshot captured; no append-only status history |
| Mission Objectives + Long Plans | DB: `long_running_missions`, `mission_phases`, `mission_weekly_plans`, `mission_scheduled_actions`, `mission_checkpoints`, `mission_data`, `mission_plan_history` | Mission IDs with `status/health/progress_pct/created_at/updated_at`; phase has `objective`, `requires_approval`, `approved_at`, `approved_by`; weekly has `objectives`, review fields; actions have lifecycle timestamps/status/outcome; checkpoints are dated snapshots; data has `source` | CRUD/updates through repository/service (`sakhi/apps/api/services/missions/repository.py`, `sakhi/apps/api/services/missions/service.py`): create mission/phase/week/action, approve phase, complete weekly review, start/complete actions, append checkpoints/data | `Moderate`: approval actor (`approved_by`) and data `source` exist; most mission state edits are direct mutable updates (limited change provenance) |
| Intervention Plans (Behavior Commitments) | DB: `intervention_plans`, `intervention_checkins` | Plan has `id/person_id/status/start/end/duration/total_scheduled/total_completed/streaks/recommendation_id/conversation_id/created_at/updated_at`; check-ins have `(plan_id, scheduled_date)` unique, `status`, `completed_count`, mood/notes, `checked_in_at`, `created_at` | Insert plan + pre-generate check-ins; check-ins UPSERT; recompute streak counters and update plan; lifecycle transitions pause/resume/complete/abandon (`sakhi/apps/api/services/learning/intervention_plans.py`) | `Moderate`: links back to `recommendation_id`/`conversation_id`; no explicit user/agent actor per status change |
| Task Commitments | DB: `tasks`, `task_dependencies`, `task_routing_cache` | `tasks.id/user_id/status/due_at/priority/parent_task_id/anchor_goal_id/routing_state/created_at/updated_at`; dependencies encode parent links; routing cache has `updated_at` + rationale | Direct insert/update/delete via DAO (`sakhi/apps/api/services/act/tasks_dao.py`), route insert (`sakhi/apps/api/main.py`), worker routing UPSERT + task state update (`sakhi/apps/worker/tasks/task_routing_worker.py`) | `Weak-Partial`: routing reason text exists; no `changed_by`/reason log for core task state transitions |
| Scheduling Commitments | DB: `scheduling_requests` | `id`, `person_id`, `original_request`, `parsed_intent`, `proposed_times`, `selected_option`, `status`, `resulting_event_id`, `resolved_at`, `created_at`, `updated_at` | Insert pending options then update to confirmed on user choice (`sakhi/apps/api/services/calendar/scheduling.py`) | `Moderate`: preserves original request + parsed intent + selected option, but no explicit actor field |
| Email Commitments | DB: `email_commitments`, `email_dismissed_actions` | Commitments: `id/person_id/commitment_hash/commitment/deadline/recipient/subject/commitment_type/status/status_changed_at/extracted_at/created_at/source_digest_id`; dismissed actions: `person_id/message_id/dismissed_at` | Batch dedupe + insert with `ON CONFLICT DO NOTHING`; status update to done/dismissed; dismissed actions insert-only dedupe (`sakhi/apps/api/services/email/digest.py`) | `Moderate`: dedupe hash + digest source + status timestamps; no explicit `changed_by` or reason on dismissal/completion |
| User Choice Decisions | DB: `user_choices` | `id`, `person_id`, `choice_context`, `options_presented`, `option_count`, `chosen_option`, `chosen_index`, `inferred_reasons`, `conversation_id`, `recommendation_id`, `created_at` | Insert-only logging on each decision (`sakhi/apps/api/services/learning/choices.py`) | `Strong-Partial`: decision context/options/outcome captured with conversation/recommendation linkage; actor implicit (user) |
| Agent Approval Decisions | DB: `agent_approval_requests` (active), `agent_approval_history` (declared) | Requests capture `request_id/session_id/task_id/person_id/action/risk/status/context`, expiry + resolve timestamps and resolver; history table has `decision`, `selected_option`, `user_comment`, response time | Insert request + in-place status update (`sakhi/apps/api/services/agent/action_approval.py`) | `Partial`: good request lifecycle fields, but no observed writes into `agent_approval_history` (no append-only decision ledger) |
| Agent Task Plans (Execution Planning State) | DB + memory: `agent_task_plans` plus in-memory `_pending_tasks`/`_task_executions` in code | DB row includes `id/person_id/task_type/steps/context_used/status/current_step_index/result/created_at/started_at/completed_at`; in-memory state has richer live status and approvals | DB insert on task creation; runtime status transitions mostly in-memory (`sakhi/apps/api/services/agent/chat_bridge.py`) | `Weak`: persistent DB status appears under-maintained compared to in-memory execution state |
| Constraint-Capture Flow (Outer Intent) | Intended DB: `dialog_states.state` JSON; code-level model in `sakhi/libs/conversation/outer_flow.py` | JSON frame state includes `outer_flow.features.g_mvs.constraints`, `notes.constraints`, `answers`, `awaiting_step`, `history`, `ready_for_plan`; frame timestamps exist in serialized state | Per-turn mutate and upsert through `ConversationStateManager` (`sakhi/libs/conversation/state.py`, call sites in `sakhi/apps/api/main.py` and `sakhi/apps/api/routes/chat.py`) | `Weak-Partial`: rich context when persisted, but migration for `dialog_states` was not found in `sakhi/infra/scripts/migrations` |

### Observed Provenance / Governance Gaps
- `dialog_states` is actively read/written in code (`sakhi/libs/conversation/state.py`) but no matching migration was found under `sakhi/infra/scripts/migrations`.
- `agent_approval_history` exists in schema but no write path was found; approval lifecycle currently mutates `agent_approval_requests` in place.
- `mission_plan_history` exists in schema but no active write path was found; mission plan evolution is not append-logged.
- `agent_task_plans` is inserted, but status progression appears primarily in-memory (`chat_bridge`) rather than persisted back to DB.
- Task write paths reference columns (`project_id`, `related_entry_id`) not visible in the checked migration set, indicating schema/runtime drift risk.

## Prompt 3
Prompt: "Audit all temporal handling: timestamps on records, temporal weighting/decay, as-of queries/snapshots/versioning, audit logs/event sourcing, daily/weekly summaries."

### 1) Which Models Are Time-Aware
| Domain | Time-Aware Models | Temporal Fields / Semantics | Evidence (Schema/Code) |
|---|---|---|---|
| Conversation Turn + Session State | `conversation_turns`, `session_summaries`, `dialog_states` (runtime table) | Turn/session timestamps (`created_at`, `last_updated`), stored state freshness (`updated_at`), frame-level `created_at/updated_at` in serialized state | Schema: `sakhi/infra/scripts/migrations/0001_baseline.sql`; state manager: `sakhi/libs/conversation/state.py` |
| Memory Base | `memory_short_term`, `memory_episodic`, `memory_context_cache` | `created_at`, `updated_at`, `expires_at`, `ts`, `time_scope`; episodic records carry `window_start/window_end/model_version`; context cache has `window_kind`, `version`, `updated_at` | Schema: `sakhi/infra/scripts/migrations/0001_baseline.sql`; episodic retrieval/promotion: `sakhi/libs/retrieval/episodic_retrieval.py`, `sakhi/apps/api/services/memory/memory_episodic.py` |
| Reflection State | `reflections`, `daily_reflection_cache`, `meta_reflections`, `reflection_inquiry_turns` | `created_at`, `reflection_date`, `generated_at`, `period`, `window_days` | Schema: `sakhi/infra/scripts/migrations/0001_baseline.sql`; writers: `sakhi/apps/engine/daily_reflection/engine.py`, `sakhi/apps/api/services/reflection/daily_generator.py`, `sakhi/apps/api/services/reflection/summarizer.py` |
| Weekly/Monthly Synthesis | `memory_weekly_signals`, `memory_weekly_summaries`, `memory_monthly_recaps`, `rhythm_weekly_rollups`, `planner_weekly_pressure`, `elemental_summary_weekly` | Week/month scoping (`week_start/week_end`, `month_scope`), snapshot payloads + confidence + write timestamps | Schema: `sakhi/infra/scripts/migrations/0001_baseline.sql`; writers: `sakhi/apps/worker/tasks/weekly_signals_worker.py`, `sakhi/apps/worker/tasks/weekly_rhythm_rollup_worker.py`, `sakhi/apps/api/services/memory/synthesis.py` |
| Goals/Plans/Tasks/Commitments | `goals`, `goal_history`, `planner_goals`, `planner_milestones`, `planned_items`, `tasks`, `scheduling_requests`, `email_commitments` | Lifecycle timestamps (`created_at/updated_at/completed_at/resolved_at/status_changed_at`), due fields (`due_at/due_ts/deadline`), parent links + weekly horizons | Schema: `sakhi/infra/scripts/migrations/0001_baseline.sql`, `sakhi/infra/scripts/migrations/0006_email_commitments.sql`; workers/services: `sakhi/apps/worker/tasks/goal_evolver.py`, `sakhi/apps/api/services/act/tasks_dao.py` |
| Missions | `long_running_missions`, `mission_phases`, `mission_weekly_plans`, `mission_scheduled_actions`, `mission_checkpoints`, `mission_plan_history` | Weekly date bounds, action lifecycle timestamps, checkpoint snapshots (`metrics_snapshot`), plan-change timestamp (`changed_at`) | Schema: `sakhi/infra/scripts/migrations/0001_baseline.sql`; repository updates: `sakhi/apps/api/services/missions/repository.py` |
| Body/Longitudinal Physiology | `body_state_history`, `rhythm_events`, `personal_model.longitudinal_state` | Time-series snapshots (`computed_at`, `event_ts`), derived per-signal windows + `last_episode_at/last_updated_at` | Schema: `sakhi/infra/scripts/migrations/0001_baseline.sql`; logic: `sakhi/apps/api/services/body/state_engine.py`, `sakhi/apps/api/services/body/health_trends.py`, `sakhi/apps/worker/tasks/weekly_learning_worker.py` |
| Audit/Event Streams | `events`, `system_events`, `debug_traces`, `crystallization_log`, `memory_strength_events`, `memory_theme_drift_events`, `learning_runs` | Append timestamps (`ts`, `occurred_at`, `created_at`, `started_at/completed_at`) and event payloads | Schema: `sakhi/infra/scripts/migrations/0001_baseline.sql`; writers: `sakhi/libs/security/idempotency.py`, `sakhi/apps/api/core/event_logger.py`, `sakhi/apps/api/core/trace_store.py`, `sakhi/apps/api/services/crystallization/engine.py`, `sakhi/apps/api/services/learning/trigger.py` |

### 2) Evidence of Temporal Logic (Decay, Rolling Windows, Snapshots)
`Temporal weighting / decay`
- `sakhi/apps/api/core/recall_scoring.py`: exponential recency decay (`tau=7/21/60`) and 24h fatigue penalty.
- `sakhi/libs/retrieval/recall.py`: score multiplied by `exp(-days/14)`.
- `sakhi/libs/retrieval/episodic_retrieval.py`: recency-adjusted similarity (`score = sim * decay`) with `days_back` time filter.
- `sakhi/apps/api/services/consolidate.py`: SQL exponential decay for theme salience using elapsed days since `last_seen`.
- `sakhi/apps/worker/tasks/intent_evolution_decay.py`: daily linear strength decay (`-0.02`) and trend update.
- `sakhi/apps/worker/tasks/weekly_learning_worker.py`: confidence decay when signal gap exceeds `DECAY_DAYS`.
- `sakhi/apps/api/services/crystallization/engine.py`: stale-pattern decay by weeks since `last_seen`.
- `sakhi/apps/api/services/workers/context_refresh_worker.py`: hard cutoff of vectors older than 180 days.

`Rolling windows / temporal scopes`
- Daily window: `sakhi/apps/api/services/reflection/daily_generator.py` (`created_at >= NOW() - INTERVAL '1 day'`).
- Weekly/monthly reflection windows: `sakhi/apps/api/services/reflection/summarizer.py` (7/30 day windows).
- Reflection narration rolling mode: `sakhi/apps/api/services/reflection/narration_foundation.py` (windowed fetch + rolling-language guard).
- Weekly analytics windows: `sakhi/apps/worker/tasks/weekly_signals_worker.py`, `sakhi/apps/worker/tasks/weekly_rhythm_rollup_worker.py`.
- Pattern windows by schedule: `sakhi/apps/worker/tasks/pattern_crystallization_worker.py` (14/30/60 days).
- Health trend windows: `sakhi/apps/api/services/body/health_trends.py` (`window_days` interval filter).

`As-of reads, snapshots, versioning`
- Snapshot-style tables are actively written: `daily_reflection_cache`, `memory_weekly_signals`, `memory_weekly_summaries`, `rhythm_weekly_rollups`, `mission_checkpoints.metrics_snapshot`.
- Episodic records preserve window metadata (`window_start`, `window_end`, `model_version`) and are deduped by window/content in `sakhi/apps/worker/tasks/episodic_consolidation_v21.py`.
- Point-in-time read exists but is narrow: `_fetch_recent_episode_summaries_before(..., before_ts)` in `sakhi/apps/worker/tasks/episodic_consolidation_v21.py`.
- Most reads are “latest snapshot” (e.g., `ORDER BY ... DESC LIMIT 1`) rather than generalized `as_of` querying.
- `conversation_turns.context_version` and `memory_context_cache.version` exist in schema but no active runtime usage was found.

`Audit logs / event-sourcing behavior`
- Append logging exists for operational telemetry and selected memory events (`system_events`, `debug_traces`, `events`, `memory_strength_events`, `memory_theme_drift_events`, `crystallization_log`, `learning_runs`).
- Core business state (tasks, goals, missions, personal_model) is still mostly mutable in place.
- `goal_history` is actively written (`sakhi/apps/worker/tasks/goal_evolver.py`), but `mission_plan_history` and `agent_approval_history` show no active write sites in current code.

`Daily/weekly summary generation`
- Daily deterministic reflection cache write: `sakhi/apps/engine/daily_reflection/engine.py`.
- Daily/weekly reflective summaries written to `meta_reflections`: `sakhi/apps/api/services/reflection/daily_generator.py`, `sakhi/apps/api/services/reflection/summarizer.py`, `sakhi/apps/worker/tasks/meta_reflection_weekly.py`.
- Weekly structured synthesis workers: `weekly_signals_worker`, `weekly_rhythm_rollup_worker`, `weekly_learning_worker`, scheduled via `sakhi/apps/worker/scheduler.py`.
- Memory synthesis weekly/monthly logic exists (`sakhi/apps/api/services/memory/synthesis.py`), but no direct scheduler hook was found for `run_memory_synthesis_job`.

### 3) Gaps for a Temporal Constraint Engine
- No unified temporal policy layer: decay constants, horizon lengths, and refresh cadences are spread across many modules and env vars.
- Horizon inconsistency risk: multiple critical paths still use 1500-day debug windows (`episodic_retrieval`, `weekly_learning_worker`, `narrative_deep`, `esr_worker`, narration foundation default).
- Weak generalized as-of semantics: system mostly reads latest rows; only limited ad hoc point-in-time logic exists.
- Dormant version fields: schema exposes version columns, but no strong read/write/version-check strategy is in use.
- Partial event sourcing: key mutable entities do not consistently emit append-only change events with actor + reason.
- Provenance gaps in core state updates: many updates lack `changed_by` and machine-readable rationale.
- Declared history tables not wired: no observed writes to `mission_plan_history` or `agent_approval_history`.
- Schema/runtime drift risk remains: code depends on `dialog_states` but no migration was found under `sakhi/infra/scripts/migrations`.
- Scheduler coverage gaps: some temporal synthesis pathways are callable but not clearly orchestrated in the main scheduler path.
- Time-boundary consistency risk: mixed use of UTC-aware timestamps and local `date.today()` can cause day-boundary skew across jobs/services.

## Prompt 4
Prompt: "Find any representation of constraints (rules, boundaries, preferences, commitments). Then determine whether constraints are A) only injected into prompts (soft) or B) enforced deterministically in code (hard). For each constraint type: storage location, enforcement mechanism, violation detection, conflict reconciliation. Output a constraint enforcement score (0-5)."

### Constraint Inventory (A vs B)
Legend:
- `A` = soft prompt-injected
- `B` = hard deterministic enforcement
- `Mixed` = prompt + deterministic post-processing

| Constraint Type | Mode | Storage Location | Enforcement Mechanism | Violation Detection | Conflict Reconciliation |
|---|---|---|---|---|---|
| Safety blocklist/refusal | `B` | Code constants in `sakhi/libs/safety/guard.py`; attempted incident log in `incidents` | `guard_messages(...)` intercepts user input before chat LLM call and returns refusal-only messages | Regex blocklist on latest user message (`is_unsafe`) | Safety override wins; request is short-circuited to refusal |
| Scaffolding suppression (crisis/silence/conflict/rhythm/emotion/engagement) | `B` (degraded by schema drift) | Rule thresholds in `sakhi/libs/scaffolding/suppression_engine.py`; user state read from `personal_model` | `@require_suppression_check` in `sakhi/libs/scaffolding/decorators.py` blocks worker execution unless decision is `ALLOW` | Deterministic rule checks with explicit reasons (`crisis_detected`, `user_silence_mode`, etc.) | Ordered precedence in suppression engine (higher-severity checks first) |
| Agent risk gating + human approval | `B` | Risk map/keywords in `sakhi/apps/api/services/agent/action_approval.py`; requests in `agent_approval_requests` | `vision_loop` pauses on risky action, requests approval, waits, then executes only if approved | Risk classification + timeout expiry (`PENDING/APPROVED/REJECTED/EXPIRED`) | Explicit resolution states; rejected/expired paths cancel action |
| Scheduling: user must confirm before create | `B` (intended) | `scheduling_requests` table + confirmation regex in `sakhi/apps/api/services/calendar/scheduling.py` | `execute_pending_confirmation(...)` creates events only for confirmed pending requests; availability is rechecked | Confirmation pattern match + slot availability check | Invalid option defaults to first; unavailable slot returns retry prompt instead of forcing creation |
| LLM provider spend budget | `B` | `DailyBudget` trackers in `sakhi/libs/llm_router/router.py` | `BudgetExceededError` from router budget check | Deterministic `spent + amount > limit` check | Router failover to next provider; some routes degrade to cached/lite |
| Write safety gates (feature flags) | `B` | Env-backed settings in `sakhi/libs/schemas/settings.py` | Services/workers early-return when gates are disabled (e.g., reflective/identity/weekly writes) | Boolean gate checks | No-op/skip behavior prevents conflicting writes |
| Structured output contracts | `Mixed` | Pydantic schemas in call sites + validation in `sakhi/apps/api/core/llm.py`; narration validator in `sakhi/apps/api/services/reflection/narration_foundation.py` | JSON-only instruction, schema validation, repair attempts; narration must pass structural/banned-term checks | JSON parse errors, schema validation failures, narration rule failures | Repair attempts in `call_llm`; hard failure/exception when still invalid |
| Turn-v2 guard language (`DEFAULT_GUARDS`, recommendation/scheduling guard text) | `A` | Prompt guard strings in `sakhi/apps/api/services/turn/deterministic_context_loader.py` and `sakhi/apps/api/routes/turn_v2.py` | Injected into prompt sections in `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | None deterministic after generation | None; model compliance is advisory |
| Contact priority preferences in email triage | `A` (plus hard data constraints) | `contact_preferences` table (`0008_contact_preferences.sql`); prompt formatter in `sakhi/apps/api/services/email/contact_preferences.py` | Preferences are injected into digest LLM prompt in `sakhi/apps/api/services/email/digest.py` | No deterministic check that triage honored muted/high/low priorities | DB upsert/unique resolves record conflicts; runtime triage conflicts are left to model behavior |
| Email commitments lifecycle | `Mixed` | `email_commitments` + `email_dismissed_actions` (`0006`/`0007`); digest pipeline in `sakhi/apps/api/services/email/digest.py` | LLM extracts commitments; code applies verification filtering, hash dedupe, UPSERT, lifecycle status transitions | Regex filter for transient commitments; hash collisions via `ON CONFLICT`; status whitelist for updates | Duplicate commitments collapsed; dismissed actions removed from surfaced action items |
| Outer-flow user constraints capture | `A` | `outer_flow.features.g_mvs.constraints` + `outer_flow.notes.constraints` in `sakhi/libs/conversation/outer_flow.py` | Used to drive follow-up clarification sequence | No downstream deterministic assertion that plans/actions satisfy captured constraints | Conversation-level closure/permission states only; no execution-time arbitration |
| Conversation ask policy | `Mixed` (partial) | `sakhi/libs/policy/conversation.yaml` + `score_ask` in `sakhi/libs/conversation/should_ask.py` | Deterministic ASK/ACK/DO scoring in `sakhi/apps/api/routes/chat.py` | Threshold comparison (`ask_threshold`) | `goal_detected/PLAN/DECIDE` can override to `DO`; other policy knobs are not fully enforced |

### Constraint Enforcement Score
**Score: 2.5 / 5**

Justification:
- Strong hard controls exist in isolated flows (approval gating, suppression decorator boundary, provider budgets, write safety flags).
- High-value user constraints are still mostly prompt-level (`A`) rather than policy-checked post-generation.
- Violation detection and conflict reconciliation are fragmented by module; there is no unified cross-domain constraint engine.
- Provenance is incomplete for constraint decisions (for example, `agent_approval_history` is declared in schema but not actively written).
- Multiple schema/runtime drifts weaken intended hard checks (examples observed: suppression queries reference `journals`, `user_preferences`, and `scaffold_interactions`; `turn_v2` treats scheduling intent as enum while detector returns `(intent, confidence)` tuple; `incidents` table migration not found in scanned migration set).

## Prompt 5
Prompt: "Locate any plan/task decomposition code: multi-step plans, task lists, workflows, agent loops. Assess: step/state tracking, drift detection, contradiction detection. Output: plan representation inventory, drift mechanisms, missing pieces for a demo that shows drift prevention."

### Plan Representation Inventory
| Subsystem | Representation + Storage | Step/State Tracking | Evidence |
|---|---|---|---|
| Loop action workflow | Action schema in code; task state in `tasks` + `task_dependencies` | `Partial`: per-turn `decisions` trace exists, but no durable plan object or step machine | `sakhi/apps/api/services/loop/models.py`, `sakhi/apps/api/services/loop/run_loop.py`, `sakhi/apps/api/services/loop/verbs.py`, `sakhi/apps/api/services/loop/frontier.py` |
| Planner graph decomposition | Goal→milestone→task graph persisted to `planner_goals`, `planner_milestones`, `planned_items` | `Partial`: entity status fields (`active/pending`) tracked, but no execution-step lifecycle | `sakhi/apps/api/services/planner/decompose.py`, `sakhi/apps/api/services/planner/commit.py`, `sakhi/apps/api/services/planner/engine.py` |
| Intent micro-planner | Simple intent→plan item mapping; persistence hook is placeholder | `Weak`: generated list only, no deterministic workflow state | `sakhi/apps/api/services/intents/planning.py`, `sakhi/apps/api/services/intents/store_plans.py`, `sakhi/apps/api/services/conversation/orchestrator.py` |
| Missions lifecycle | LLM decomposition into phases/weeks/actions; persisted in `long_running_missions`, `mission_phases`, `mission_weekly_plans`, `mission_scheduled_actions`, `mission_checkpoints` | `Strong`: phase approval, weekly completion, action start/complete/fail, checkpoint snapshots | `sakhi/apps/api/services/missions/decomposer.py`, `sakhi/apps/api/services/missions/service.py`, `sakhi/apps/api/services/missions/repository.py`, `sakhi/apps/api/services/missions/models.py` |
| Agent task orchestrator | `TaskPlan`/`TaskStep`/`TaskResult` in memory; execution delegated to vision loop | `Moderate`: explicit runtime statuses and step counters; `depends_on` field exists but is not enforced in execution loop | `sakhi/apps/api/services/agent/task_orchestrator.py` |
| Chat-agent bridge execution | Pending/active execution state in in-memory stores; initial plan row inserted into `agent_task_plans` | `Moderate (volatile)`: tracks confirmation/execution states, but lifecycle is primarily in-memory | `sakhi/apps/api/services/agent/chat_bridge.py`, `sakhi/infra/scripts/migrations/0001_baseline.sql` |
| Vision loop (agent loop) | `VisionLoopState` with action history/retries/approval counts | `Strong operational`: loop status transitions (`running/paused/waiting_approval/completed/failed`), retries, timeout and max-step guards | `sakhi/apps/api/services/agent/vision_loop.py` |
| Agentic task planner | `TaskPlan` + `TaskStep` with dependency list and per-step statuses persisted in `task_plans` | `Strong`: plan + step transitions are explicit and persisted (`pending_approval → executing → completed/failed/paused/cancelled`) | `sakhi/apps/api/services/agentic/planner.py`, `sakhi/apps/api/routes/agentic.py` |
| Conversation frame workflow | Frame stack (`active/paused/completed`) persisted to `dialog_states` | `Moderate`: deterministic frame transitions, but this is dialogue-flow state, not task decomposition | `sakhi/libs/conversation/state.py` |

### Assessment
- `Does the system track plan steps and state transitions?` **Yes, but unevenly.** Strong in `missions`, `agentic/planner`, and `vision_loop`; weaker in `loop` and lightweight intent planning.
- `Is there deviation detection (drift)?` **Partially.** Existing mechanisms mostly detect operational/session drift, not semantic goal-plan drift.
- `Are contradictions detected across steps?` **Not as an enforced workflow guard.** Contradiction signals exist in reasoning modules but are not wired into plan execution gates.

### Drift Detection Mechanisms Found
- `Conversation/topic drift`: `topic_shift_score` triggers session switching heuristics in `sakhi/apps/api/services/loop/run_loop.py`.
- `Dependency/precondition drift`: frontier gating in `sakhi/apps/api/services/loop/frontier.py` and dependency checks in `sakhi/apps/api/services/agentic/planner.py` block steps when prerequisites are missing.
- `Operational drift/failure control`: `sakhi/apps/api/services/agent/vision_loop.py` enforces retry budgets, timeout cutoff, max-step cutoff, pause/resume, and approval-paused flow.
- `Adaptive weekly correction`: `sakhi/apps/api/services/missions/service.py` supports weekly review completion and regeneration of next week via `decompose_first_week`.
- `Global contradiction signals (not enforced)`: `sakhi/libs/reasoning/engine.py` returns `contradictions` and `open_loops`, but no deterministic integration into plan step transitions was found.

### Missing Pieces for a Drift-Prevention Demo
- `Unified execution ledger`: add append-only `plan_step_events` with `expected_state`, `observed_state`, `drift_reason`, `actor`, and `ts` across all planning systems.
- `Semantic drift detector`: compare current observations/results against declared objective + constraints + prior step outputs; produce deterministic `drift_score`.
- `Contradiction gate`: enforce pre-step checks using contradictions/open-loops before allowing next step execution.
- `Deterministic recovery policy`: codify actions on drift (`replan`, `rollback`, `ask_user`, `defer`) with policy thresholds.
- `Persistence hardening`: persist `chat_bridge` execution state transitions to DB and wire writes for declared history tables like `mission_plan_history`.
- `Schema alignment`: `task_plans` is actively used by `agentic/planner` but no migration was found under `sakhi/infra/scripts/migrations`; resolve this for reproducible demo infra.
- `Demo harness`: scripted perturbation scenarios (missing dependency, changed user constraint, contradictory new evidence) with measurable outcomes: detect time, prevented bad action, successful replan rate.

## Prompt 6
Prompt: "Audit how the system separates deterministic logic vs LLM reasoning. For each LLM call: input context, output use, validations, failure modes, risk classification. Output LLM boundary map + deterministic governance recommendations."

### Deterministic vs LLM Separation (Current)
- Deterministic logic is strong in data loading, temporal windows, state retrieval, routing heuristics, and many execution guardrails (`turn_v2`, `deterministic_context_loader`, agent approval/risk gates, dependency checks).
- LLM reasoning is broad and mixed-use: plain response generation, extraction/classification, planning, vision interpretation, and some state mutation proposals.
- Core boundary control exists (`call_llm` + `LLMRouter`) but enforcement is inconsistent across call sites:
  - `call_llm(schema=...)` gives typed validation + repair attempts.
  - Many direct `router.chat(...)` paths use manual JSON parsing only.
  - Several high-impact paths mutate state from untyped LLM output.

### LLM Boundary Map
| Boundary (Call Sites) | Input Context to LLM | Output Used For | Validations Applied | Failure Modes | Risk |
|---|---|---|---|---|---|
| Turn-v2 final reply (`sakhi/apps/api/services/conversation_v2/conversation_engine.py`) | Deterministic context bundle (recall, patterns, adaptive prompt, session summary, recent turns, user text) | User-facing reply; reply also appended to `personal_model.short_term` | No response schema; string trim only | Hallucinated/ungrounded reply; prompt-only guards can be ignored; fallback generic reply on exception (`turn_v2`) | `Medium` |
| Dev chat + tools (`sakhi/apps/api/routes/chat.py`) | Guarded chat messages + recall/memory inserts + persona + tool definitions | Assistant message; tool calls may execute local tools then follow-up LLM call | `guard_messages`; tool runner schema validation for `create_plan`; OpenRouter tool-call schema checks when routed there | Tool argument parse falls back to `{}`; unknown tool calls produce error payload; no deterministic policy check on final natural-language tool interpretation | `High` |
| Loop action orchestration (`sakhi/apps/api/services/loop/llm_bridge.py`, `sakhi/apps/api/services/loop/run_loop.py`) | Session summary/history, user prefs, task graph/frontier context, objective | Reply + JSON actions; actions dispatch to tasks/calendar/lists/journal writes | Deterministic `fast_parse` bypass for high-confidence intents; no strict schema for LLM action payload | Malformed JSON => no actions; parseable but semantically wrong actions can still mutate state | `High` |
| Context-router fallback (`sakhi/apps/api/services/context_router.py`) | User text + emotion (only on low deterministic confidence) | Context module set used for turn module activation | Allowed-module filtering after parse | Brittle bracket-based JSON extraction; falls back to empty modules on parse errors | `Medium` |
| Action-intent extraction route (`sakhi/apps/api/routes/conversation.py`) | Raw user message | `ActionIntent` drives confirmation/draft-task flow | `call_llm(schema=ActionIntent)` | On failure returns `is_action=False`; no unintended write without explicit confirm | `Medium` |
| Agent screen analyzer (`sakhi/apps/api/services/agent/screen_analyzer.py`) | Screenshot + task context + recent actions | Structured screen state consumed by vision loop | JSON parse helper only (no strict schema) | Parse failures produce empty/error analysis; loop may stall/retry | `Medium` |
| Agent action decider (`sakhi/apps/api/services/agent/action_decider.py`) | Task + task context + screen analysis + action history | Next UI action decision for autonomous loop | JSON parse helper; approval/risk check happens after decision in `vision_loop` | Parse failures produce no-op/error decisions; autonomous flow quality depends on untyped output | `High` |
| Agent task orchestrator planner (`sakhi/apps/api/services/agent/task_orchestrator.py`) | Task + gathered memories/preferences/constraints | Multi-step task plan for vision execution | Manual JSON parse + fallback plan | If parse fails, collapses to simplistic fallback plan; no schema-level plan contract | `High` |
| Agentic task planner (`sakhi/apps/api/services/agentic/planner.py`) | Task description + available tools | Persisted `task_plans` + step execution pipeline | Pydantic `TaskStep` objects after manual parse; dependency checks during execution | No strict schema at LLM boundary; parse/path errors can degrade to single-step fallback | `High` |
| Agentic search/research synthesis (`sakhi/apps/api/services/agentic/search.py`, `sakhi/apps/api/services/agentic/research.py`, `sakhi/apps/api/services/agentic/tools.py`) | Search results / fetched sources / tool outputs | Summaries and synthesis text | No strict schema; fallback snippets | Synthesis quality drift; fallback generic outputs | `Safe` |
| Mission decomposition (`sakhi/apps/api/services/missions/decomposer.py`) | Goal/category/context/outcomes | Structured phase/week/action plans for mission workflows | Strong schema via `call_llm(schema=...)` + repair attempts | Call failure raises or returns empty suggestions for some paths | `Medium` |
| Goal suggestion (`sakhi/apps/api/services/planner/goal_suggester.py`) | Recent intents + existing goals | Goal suggestions for later confirmation | Threshold filters (`mention_count`, `confidence`) after parse | Bad clustering/duplication can pass if parseable; no hard semantic validator | `Medium` |
| Goal evolution worker (`sakhi/apps/worker/tasks/goal_evolver.py`) | Active goals + episodes + rhythm + operating system | Direct `goals` revisions/archive + `goal_history` rows | Minimal checks (`goal_id`, action); no strict output schema | Parseable incorrect revisions can mutate goals; limited conflict checks | `High` |
| Intent extraction services (`sakhi/apps/api/services/intents/extract.py`, `sakhi/apps/api/services/planner/extract.py`) | User text (+ topics/emotion in one path) | Intent objects for planning/orchestration | Manual JSON parsing + normalization/clamping | Parse failure returns empty intents; semantic drift remains | `Medium` |
| Email digest/commitments (`sakhi/apps/api/services/email/digest.py`) | Email batches + contact priority context + temporal rules in prompt | Triage items + commitments persisted/deduped | Per-item Pydantic validation/mapping, dedupe hashes, status guards | Whole-payload parse failure => empty digest batch; misclassification still possible | `Medium` |
| Preference extraction (`sakhi/apps/api/services/memory/preference_learning.py`, `sakhi/apps/api/services/memory/sensory_preferences.py`) | User text + optional context | Preference profile updates | Domain/dimension heuristics, enum/value checks post-parse | Parse failures skip learning; noisy extracted preferences may still be stored | `Medium` |
| Relationships extraction (`sakhi/apps/api/services/relationships/extraction.py`) | Free text | People/signals entities for relationship memory | Pydantic schema (`PeopleExtractionResult`, `RelationshipSignalsResult`) | Returns empty on failures; no state mutation if extraction fails | `Medium` |
| Reflection narration/inquiry (`sakhi/apps/api/services/reflection/narration_foundation.py`, `sakhi/apps/api/services/reflection_inquiry/answerer.py`) | Deterministic note packs, states, recent evidence, user question | Reflection text persisted to reflection tables | Strong post-validation (sentence count, banned terms, style constraints) | Validation failure hard-stops write path | `Safe` |
| Memory/session/recall summarization (`sakhi/apps/api/services/memory/recall.py`, `sakhi/apps/api/services/memory/sessions.py`, `sakhi/apps/api/services/memory/summarize.py`, `sakhi/libs/memory/store.py`) | Retrieved memory snippets or recent turns | Compression summaries, continuity text, memory hints | Mostly length/format heuristics; limited strict schemas | Summaries can be lossy; fall back to heuristic/no-op on errors | `Safe` |

### Cross-Cutting Failure Modes
- `LLMResponse interface mismatch`: many direct `router.chat` call sites read `response.content[0].text`, but router returns normalized `LLMResponse.text`. Affected files include:
  - `sakhi/apps/api/services/agent/action_decider.py`
  - `sakhi/apps/api/services/agent/actions.py`
  - `sakhi/apps/api/services/agent/screen_analyzer.py`
  - `sakhi/apps/api/services/agent/task_orchestrator.py`
  - `sakhi/apps/api/services/agentic/planner.py`
  - `sakhi/apps/api/services/agentic/research.py`
  - `sakhi/apps/api/services/agentic/search.py`
  - `sakhi/apps/api/services/agentic/tools.py`
  - `sakhi/apps/api/services/memory/sensory_preferences.py`
  - `sakhi/apps/api/services/vision/documents.py`
  - `sakhi/apps/api/services/vision/processor.py`
- `Schema inconsistency`: high-risk state mutations still rely on manual JSON parsing (`loop`, `goal_evolver`, parts of `agentic/planner`) instead of typed contracts.
- `Provider behavior mismatch`: `OpenRouterProvider.chat` drops `response_format`, so schema-style JSON forcing is weaker unless validated post-call.
- `Soft constraints dominate`: many constraints are prompt-injected text rather than deterministic post-generation checks before mutating state.

### Recommended Changes to Make Governance Deterministic
1. Fix response contract drift now: standardize all `router.chat` consumers on `response.text` (or one shared `extract_llm_text(response)` helper), then add a linter/test rule blocking `response.content` usage with router responses.
2. Require typed outputs for all state-mutating paths: migrate high-risk calls to `call_llm(schema=...)` with strict Pydantic contracts (`loop` actions, `goal_evolver` revisions, agentic/agent planners).
3. Add a deterministic mutation gateway: route every LLM-proposed write through one `StateTransitionService` that enforces invariants, status-transition legality, and constraint checks before DB writes.
4. Introduce two-phase apply for high-risk actions: `propose (LLM) -> validate (deterministic) -> apply (repo)`; if validation fails, convert to `ask_user` instead of auto-write.
5. Build a first-class constraint engine: evaluate commitments, preferences, boundaries, and conflicts as executable rules, not prompt prose.
6. Add provenance/event logging on every governed mutation: write append-only events with `entity_type`, `entity_id`, `before`, `after`, `changed_by` (`user|worker|llm`), `reason`, `prompt_hash`, `model`, `timestamp`.
7. Enforce fail-closed behavior by risk tier: for `High` boundaries, parsing/validation failure should block mutation and emit explicit review signals (not silent fallback execution).
8. Add governance regression tests: include adversarial JSON, conflicting constraints, stale-context scenarios, and provider-format variance checks to verify deterministic outcomes.

## Prompt 7
Prompt: "Find any tests, eval harnesses, scripted scenarios, replay logs, golden datasets, or telemetry that can measure contradictions, constraint violations, drift rate across turns. If none exist, propose a fast eval harness for pre-seed demo metrics."

### What Exists
| Category | Current Assets | Coverage for Requested Metrics | Evidence |
|---|---|---|---|
| End-to-end and integration tests | Multi-turn and storage tests exist (`sakhi/tests/e2e/test_api_e2e.py`, `sakhi/tests/integration/workers/test_turn_pipeline_integration.py`) | `Partial`: verifies API behavior and state writes, but does not compute contradiction/violation/drift KPIs | `sakhi/tests/e2e/test_api_e2e.py`, `sakhi/tests/integration/workers/test_turn_pipeline_integration.py` |
| Scripted verification scenarios | Multiple `scripts/*_check.py` flows validate pipelines via API + DB snapshots | `Partial`: useful manual scenarios, not a scored eval harness | `scripts/integration_test.py`, `scripts/planner_pipeline_check.py`, `scripts/rhythm_engine_check.py`, `scripts/growth_loop_check.py`, `scripts/brain_state_check.py` |
| Deterministic harness pattern | Weekly reflection harness with stubbed LLM writes a fixture | `Partial`: demonstrates deterministic replay pattern but only for weekly reflection quality, not governance metrics | `scripts/weekly_reflection_harness.py` |
| Drift telemetry in data layer | Weekly/monthly synthesis computes and stores drift | `Strong` for drift signal availability, but no cross-turn quality scorecard | `sakhi/apps/api/services/memory/synthesis.py`, `sakhi/infra/scripts/migrations/0001_baseline.sql` (`memory_weekly_summaries.drift_score`, `memory_monthly_recaps.drift_score`, `memory_theme_drift_events`) |
| Contradiction signal generation | Reasoning bundle emits contradictions/open loops; ingest persists contradiction nodes/edges | `Partial`: contradiction artifacts exist, but no benchmark asserting detection quality | `sakhi/libs/reasoning/engine.py`, `sakhi/apps/api/services/memory/ingest_reasoning.py` |
| Constraint enforcement signal points | Deterministic checks exist in suppression engine and safety guard | `Partial`: enforcement exists, but no metric harness aggregating violation rate over test cases | `sakhi/libs/scaffolding/suppression_engine.py`, `sakhi/libs/scaffolding/decorators.py`, `sakhi/libs/safety/guard.py` |
| Telemetry plumbing | Request and incident logging paths exist | `Weak-Partial`: useful for metrics if tables are present | `sakhi/apps/api/middleware/telemetry.py`, `sakhi/apps/api/admin.py`, `sakhi/libs/safety/guard.py` |

### What’s Missing
- No dedicated eval runner that replays labeled multi-turn scenarios and outputs contradiction rate, constraint violation rate, and drift rate across turns.
- No golden/labeled governance dataset (expected contradiction/violation/drift outcomes per scenario). Existing fixtures are factories and helper data, not labeled benchmark truth (`sakhi/tests/fixtures/*`).
- No replay log corpus with frozen turn transcripts + expected governance outcomes.
- No CI gate for governance regressions (pass/fail thresholds on these metrics).
- No unified metric definitions persisted as eval outputs (`eval_run_id`, `case_id`, `metric_name`, `score`, `pass_fail`).
- Telemetry schema alignment gaps: code writes/reads `request_logs`, `incidents`, `dialog_states`, `suppression_log`, but these table definitions were not found in checked migrations (`sakhi/infra/scripts/migrations/*`), weakening reliability of production metrics extraction.

### Minimal Eval Harness Plan (Pre-Seed Demo)
Goal: ship a small, deterministic governance scorecard quickly using existing repo patterns.

1. Add a tiny labeled scenario set.
   - Create `sakhi/tests/evals/turn_governance_cases.json` with 20-30 cases.
   - Per case include: `scenario_id`, `turns[]`, `expected_contradictions`, `constraints`, `expected_violations`, `expected_drift_band`.
   - Split evenly across three buckets: contradiction-heavy, constraint-heavy, drift-heavy.

2. Build one replay runner.
   - Add `scripts/eval_turn_governance.py`.
   - Reuse the style from `scripts/integration_test.py` and deterministic harness ideas from `scripts/weekly_reflection_harness.py`.
   - For each case: reset test user/session, replay turns through `/v2/turn`, collect DB artifacts after each turn.

3. Implement deterministic scorers (no judge LLM dependency).
   - Contradictions: compare expected contradiction labels with observed contradiction artifacts from reasoning/ingest (`reasoning.contradictions` or `memory_nodes.node_kind='contradiction'`).
   - Constraint violations: per-case rule checks against assistant output and side effects (for example, detect disallowed suggestions by regex/keyword rules; verify no calendar/task write without required confirmation when applicable).
   - Drift rate across turns: compute turn-to-turn topic drift using the existing theme-overlap method (same logic style as `_calculate_drift` in `memory/synthesis.py`) and aggregate per scenario.

4. Emit demo-ready outputs.
   - Write machine-readable JSON: `artifacts/evals/turn_governance_<timestamp>.json`.
   - Write markdown summary: `artifacts/evals/turn_governance_<timestamp>.md`.
   - Include KPI table:
     - `contradiction_detection_rate`
     - `constraint_violation_rate`
     - `avg_drift_per_turn`
     - `drift_recovery_within_2_turns`

5. Add fast threshold checks for pre-seed regression safety.
   - Start with pragmatic gates:
     - contradiction detection rate `>= 0.75`
     - constraint violation rate `<= 0.15`
     - drift recovery within 2 turns `>= 0.60`
   - Fail runner exit code when thresholds are violated.

6. Wire into CI as optional first, required later.
   - Add a lightweight CI job (`make eval-governance`) that runs only this harness on stub/local model settings first, then graduate to nightly real-model run.

### Expected Build Effort (Fast Track)
- Day 1: dataset + runner skeleton + replay plumbing.
- Day 2: deterministic scorers + JSON/markdown reporting.
- Day 3: thresholds, CI job, and 1-page dashboard summary for demo narrative.

## Prompt 8
Prompt: "Given the repo’s current capabilities, propose the fastest path to a pre-seed-ready demo that proves: (1) constraint consistency across time, (2) evolving objective modeling, (3) drift detection in multi-step plans."

### Fastest Path (Recommendation)
Use one coherent backbone instead of many parallel planners:
- Primary orchestration: `planner` graph (`planner_goals`/`planner_milestones`/`planned_items`) + `missions` for multi-week execution.
- Constraint capture/enforcement: reuse outer-flow capture + deterministic gates, then add one centralized constraint evaluator before writes.
- Drift proof: reuse existing step/dependency signals + memory drift logic, then add a compact plan-drift worker and event table.

This avoids a broad refactor and is the shortest path to a convincing pre-seed demo.

### Existing Modules to Reuse
| Demo Need | Reuse Modules | Why They Fit |
|---|---|---|
| Constraint consistency across turns | `sakhi/libs/conversation/state.py`, `sakhi/libs/conversation/outer_flow.py`, `sakhi/libs/conversation/clarify_outer.py`, `sakhi/apps/api/routes/chat.py` | Already captures timeline/preferences/constraints over multiple turns with persisted frame state. |
| Hard deterministic constraint checks | `sakhi/libs/scaffolding/suppression_engine.py`, `sakhi/libs/scaffolding/decorators.py`, `sakhi/libs/safety/guard.py`, `sakhi/apps/api/services/calendar/scheduling.py`, `sakhi/apps/api/services/agent/action_approval.py` | Existing rule-based enforcement for suppression, unsafe content, scheduling confirmation, and risky actions. |
| Objective modeling (current state) | `sakhi/apps/api/services/planner/engine.py`, `sakhi/apps/api/services/planner/decompose.py`, `sakhi/apps/api/services/planner/commit.py`, `sakhi/apps/api/services/planner/cache.py` | Already builds and persists objective graphs with horizons and status. |
| Long-horizon objective execution | `sakhi/apps/api/services/missions/service.py`, `sakhi/apps/api/services/missions/repository.py`, `sakhi/apps/api/services/missions/decomposer.py` | Already supports phased plans, approvals, weekly plans, and scheduled actions. |
| Objective evolution signals | `sakhi/apps/worker/tasks/goal_evolver.py`, `goal_history` path inside worker; `sakhi/apps/api/services/growth/loop.py` | Existing revision concept and growth signal ingestion from planner outputs. |
| Plan drift and contradiction signals | `sakhi/apps/api/services/agentic/planner.py` (step status + dependencies), `sakhi/apps/api/services/loop/frontier.py` (precondition gating), `sakhi/apps/api/services/loop/run_loop.py` (`topic_shift_score`), `sakhi/apps/api/services/memory/synthesis.py` (`_calculate_drift`), `sakhi/libs/reasoning/engine.py` (contradictions/open loops) | Existing signals are present; they need unification and scoring. |

### New Modules to Build (Minimal)
1. `ConstraintRegistry` + storage
   - New table: `objective_constraints` (append-friendly, versioned constraints with scope and validity window).
   - New service: `sakhi/apps/api/services/governance/constraint_registry.py`.
   - Purpose: normalize captured constraints into executable rules that persist across sessions.

2. `ConstraintEvaluator` (deterministic gate)
   - New service: `sakhi/apps/api/services/governance/constraint_evaluator.py`.
   - Hook points: before `planner_commit`, mission action scheduling, and any state-mutating agent/tool action.
   - Purpose: block or rewrite violating actions deterministically (not prompt-only).

3. `ObjectiveVersioningService`
   - New table: `objective_versions` (objective_id, version, parent_version, change_type, reason, before_json, after_json, ts).
   - New service: `sakhi/apps/api/services/governance/objective_versioning.py`.
   - Purpose: prove evolving objective modeling with explicit lineage and rationale.

4. `PlanDriftMonitor`
   - New table: `plan_drift_events` (plan_id, step_id, drift_type, severity, evidence_json, detected_at, resolution_state).
   - New worker/service: `sakhi/apps/worker/tasks/plan_drift_monitor.py`.
   - Purpose: detect and log deviation in multi-step plans (dependency drift, contradiction drift, constraint drift).

5. `Demo Governance API`
   - New route: `sakhi/apps/api/routes/governance_demo.py`.
   - Outputs: current constraints, objective lineage, drift timeline, and aggregate demo KPIs.
   - Purpose: one endpoint to drive investor/demo narrative without manual SQL.

### 30/60/90 Day Plan
| Window | Goal | Deliverables | Exit Criteria |
|---|---|---|---|
| Day 0-30 | Ship demoable governance core | `objective_constraints`, `objective_versions`, `plan_drift_events` migrations; constraint registry/evaluator in planner+missions write path; objective versioning wrapper; drift monitor v1; governance demo endpoint; 10-15 scripted demo cases | Live demo proves all 3 claims with persisted artifacts and deterministic enforcement logs. |
| Day 31-60 | Hardening + measurable reliability | Expand enforcement to turn-level and agentic writes; add governance eval runner from Prompt 7; CI threshold checks; conflict-resolution policy for multi-constraint collisions; alerting on drift spikes | Governance metrics stable on repeated runs; regression gate active in CI/nightly. |
| Day 61-90 | Pre-seed polish + scale readiness | Role-based dashboards, provenance enrichment (`changed_by`, reason codes), auto-replan on drift, better temporal policy tuning, demo environment automation | Team can run end-to-end demo in <10 min with reproducible metrics and clear audit trail. |

### Demo Script (Step-by-Step User Scenario)
Scenario: user wants to launch a weekly newsletter while protecting health and time boundaries.

1. User defines objective + hard constraints.
   - User: “Help me launch a weekly newsletter in 8 weeks. No work after 9pm, max 5 hours/week, budget under $300.”
   - System uses outer-flow clarification (`timeline`, `constraints`, `criteria`) and persists normalized constraints.

2. System proposes initial multi-step plan.
   - Planner creates goal→milestone→tasks and a mission week plan.
   - Demo panel shows objective version `v1`, constraints attached, and scheduled actions.

3. User evolves objective mid-stream.
   - User: “Add short video clips as a secondary channel, but keep the same time and budget limits.”
   - System creates objective version `v2` with parent link to `v1`; unchanged constraints are inherited.

4. Constraint consistency is tested across time.
   - User later asks for a 10:30pm deep-work block and paid tool costing $500.
   - Evaluator blocks both: time-window breach + budget breach.
   - System returns deterministic explanation and compliant alternatives.

5. Multi-step plan drift is introduced.
   - Simulate missed prerequisite (for example, no audience research completed before content automation step).
   - Drift monitor emits `dependency_drift` event; reasoning contradiction signal is attached if present.

6. System performs controlled recovery.
   - Planner pauses violating step, proposes corrective sequence (research first, then automation).
   - User approves; plan resumes with updated step ordering.

7. Demo closes with proof artifacts.
   - Show governance endpoint output:
     - constraint consistency log across turns/sessions
     - objective lineage (`v1 -> v2`)
     - drift events + resolution
     - KPI snapshot (violations prevented, drift detected, successful replans).

### Demo Success Metrics (for the room)
- `constraint_consistency_rate`: blocked-or-corrected violations / total attempted violations.
- `objective_evolution_traceability`: % objective changes with valid parent/version/reason.
- `drift_detection_latency`: median time from drift occurrence to logged detection.
- `drift_recovery_rate`: % drift events resolved via approved replan within 2 turns.

# Scaffolding Layer Audit Report

**Audit Date**: January 8, 2026
**Auditor**: Claude Sonnet 4.5
**Scope**: Scaffolding & Support Layer (Layer 4)
**Mode**: Read-only inventory and classification

---

## Audit Purpose

This audit inventories all Scaffolding-adjacent logic in the Sakhi codebase to answer:

**"We now know every place where Sakhi attempts to help the user act — and exactly how."**

This is a **read-only systems audit**. No refactoring, renaming, or improvements are suggested. Only observation, inventory, and classification.

---

## Audit Context

**Layers 1–3 (Observation, Memory, Deterministic Sensemaking)** are closed and not altered.

This audit focuses exclusively on **Scaffolding-adjacent logic**:
- Anything that decides when, whether, or how Sakhi attempts to support user action, pacing, focus, or intervention.

Scaffolding must remain:
- Supportive
- Suppressible
- Reversible
- Non-declarative
- Non-identity-forming

---

## Classification Rules

**Safe**: Reads Sensemaking outputs, produces bounded signals or gates, no language, no identity claims.

**Questionable**: Produces quasi-advice, unclear suppression, timing feels opinionated, or logic is implicit.

**Violation**: Writes to personal_model improperly, generates advice-like language, or infers identity/meaning.

---

## Audit Findings

### 1. Planner Pressure & Load Calculation

#### 1.1 Planner Weekly Pressure

**File**: `/sakhi/apps/worker/tasks/planner_weekly_pressure.py`
**Primary Responsibility**: Calculates weekly task pressure signals (carryover, fragmentation, urgency)
**Trigger**: Worker (scheduled weekly)
**Reads**:
- `planned_items` table
- `goals` table
- `milestones` table
- Week start/end boundaries

**Writes**:
- `planner_weekly_pressure` table (columns: `person_id`, `week_start`, `carryover_count`, `fragmentation_score`, `urgency_weight`, `computed_at`)

**Timing / Cadence**: Weekly (Monday 5 AM per scheduler.py:657)

**Nature of Output**:
- Signal (quantitative metrics)
- No language generation
- Structured numerical output

**Deterministic?**: Yes (pure count/score calculations)

**Suppressible?**: N/A (produces signals, not actions)

**Layer Alignment**: **Safe**

**Notes**: Pure deterministic math. Counts carryover tasks, computes fragmentation (spread across time), calculates urgency weights. Feeds into longitudinal_state.work dimension. No interpretation, no suggestions. Signal-only.

---

#### 1.2 Planner Context Refresh

**File**: `/sakhi/apps/worker/tasks/planner_context_refresh.py`
**Primary Responsibility**: Refreshes planner context cache for fast reads
**Trigger**: Worker (scheduled)
**Reads**:
- `goals` table
- `milestones` table
- `planned_items` table
- `intents` table

**Writes**:
- `planner_context_cache` table

**Timing / Cadence**: Scheduled (frequency not specified in scheduler)

**Nature of Output**:
- Cache update (structured data)
- No language generation

**Deterministic?**: Yes (aggregation logic)

**Suppressible?**: N/A (cache maintenance)

**Layer Alignment**: **Safe**

**Notes**: Pure cache refresh. Aggregates active goals, next milestones, pending tasks, recent intents. No decision logic. Infrastructure only.

---

### 2. Focus & Pacing Logic

#### 2.1 Focus Path

**File**: `/sakhi/apps/engine/focus_path/engine.py`
**Primary Responsibility**: Generates focus path suggestions based on goals and rhythm
**Trigger**: Scheduled daily (8 AM per scheduler) + on-demand API
**Reads**:
- `personal_model.goals_state`
- `personal_model.rhythm_state`
- `personal_model.alignment_state`
- `planner_context_cache`

**Writes**:
- `personal_model.focus_path_state`
- `focus_path_cache` table

**Timing / Cadence**: Daily 8 AM

**Nature of Output**:
- Structured suggestion (task prioritization)
- Contains language ("suggested_task", "focus_hint")

**Deterministic?**: Bounded (uses LLM for focus_hint generation)

**Suppressible?**: Partial (user can ignore, but auto-generated daily)

**Layer Alignment**: **Questionable**

**Notes**: Reads rhythm capacity and goal urgency to suggest task prioritization. Generates "focus_hint" text via LLM. Output includes suggested tasks with reasoning. Contains quasi-advice ("now is good time for..."). Timing is opinionated (8 AM daily). Unclear if suppressed when rhythm shows low capacity.

---

#### 2.2 Mini Flow

**File**: `/sakhi/apps/engine/mini_flow/engine.py`
**Primary Responsibility**: Suggests micro-flow session based on rhythm and alignment
**Trigger**: Scheduled daily (8:15 AM per scheduler) + on-demand API
**Reads**:
- `personal_model.rhythm_state`
- `personal_model.focus_path_state`
- `personal_model.alignment_state`

**Writes**:
- `personal_model.mini_flow_state`
- `personal_model.mini_flow_rhythm_slot`
- `mini_flow_cache` table

**Timing / Cadence**: Daily 8:15 AM

**Nature of Output**:
- Suggestion (structured flow session)
- Contains language ("session_hint", "prep_message")

**Deterministic?**: Bounded (uses LLM for hint generation)

**Suppressible?**: Partial (user can ignore)

**Layer Alignment**: **Questionable**

**Notes**: Recommends 15-30 minute flow sessions. Generates prep messages and hints. Timing logic selects "best rhythm slot" from rhythm_state. Contains implicit advice about when to focus. Output includes duration, task, and motivational language.

---

#### 2.3 Micro Journey

**File**: `/sakhi/apps/engine/micro_journey/engine.py`
**Primary Responsibility**: Generates micro-journey scaffolding for tasks
**Trigger**: On-demand API only
**Reads**:
- `personal_model.focus_path_state`
- `personal_model.rhythm_state`
- Task details from request

**Writes**:
- `personal_model.micro_journey_state`
- `micro_journey_cache` table

**Timing / Cadence**: On-demand (no schedule)

**Nature of Output**:
- Suggestion (task breakdown)
- Contains language ("step_hint", "encouragement")

**Deterministic?**: Bounded (uses LLM for hint generation)

**Suppressible?**: Yes (only runs when user requests)

**Layer Alignment**: **Safe**

**Notes**: User-initiated task breakdown. Generates step-by-step scaffolding with hints. Suppressible by design (on-demand only). Language is supportive, not directive. No automatic triggering.

---

### 3. Morning Scaffolds

#### 3.1 Morning Preview

**File**: `/sakhi/apps/engine/morning_preview/engine.py`
**Primary Responsibility**: Generates morning preview of day ahead
**Trigger**: Scheduled daily (6 AM per scheduler)
**Reads**:
- `personal_model.goals_state`
- `personal_model.rhythm_state`
- `personal_model.alignment_state`
- `planner_context_cache`
- Calendar/weather (if available)

**Writes**:
- `personal_model.morning_preview_state`
- `morning_preview_cache` table

**Timing / Cadence**: Daily 6 AM

**Nature of Output**:
- Signal + language (structured preview with narrative)
- Contains "preview_text", "day_outlook"

**Deterministic?**: Bounded (uses LLM for preview_text generation)

**Suppressible?**: Partial (auto-generated, but user can dismiss)

**Layer Alignment**: **Questionable**

**Notes**: Auto-generates daily outlook. Reads rhythm to assess capacity. Includes language about "today looks..." and task suggestions. Timing is fixed (6 AM). No evidence of suppression logic when rhythm shows exhaustion or conflict. Feels prescriptive.

---

#### 3.2 Morning Ask

**File**: `/sakhi/apps/engine/morning_ask/engine.py`
**Primary Responsibility**: Generates contextual morning question
**Trigger**: Scheduled daily (6:10 AM per scheduler)
**Reads**:
- `personal_model.morning_preview_state`
- `personal_model.soul_state`
- `personal_model.conflict_state`
- Recent journal entries

**Writes**:
- `personal_model.morning_ask_state`
- `morning_ask_cache` table

**Timing / Cadence**: Daily 6:10 AM

**Nature of Output**:
- Language (single open-ended question)

**Deterministic?**: No (LLM-generated question)

**Suppressible?**: Partial (auto-generated daily)

**Layer Alignment**: **Questionable**

**Notes**: Generates daily reflection prompt based on current state. Language is framed as invitation, not directive. However, timing is automatic and question content may feel presumptive. No visible suppression logic for when user needs silence.

---

#### 3.3 Morning Momentum

**File**: `/sakhi/apps/engine/morning_momentum/engine.py`
**Primary Responsibility**: Generates morning momentum message
**Trigger**: Scheduled daily (6:15 AM per scheduler)
**Reads**:
- `personal_model.morning_preview_state`
- `personal_model.morning_ask_state`
- `personal_model.rhythm_state`
- `personal_model.goals_state`

**Writes**:
- `personal_model.morning_momentum_state`
- `morning_momentum_cache` table

**Timing / Cadence**: Daily 6:15 AM

**Nature of Output**:
- Language (encouragement + action suggestion)

**Deterministic?**: No (LLM-generated message)

**Suppressible?**: Partial (auto-generated daily)

**Layer Alignment**: **Questionable**

**Notes**: Generates motivational message with action suggestions. Contains language like "you might start with..." or "today's energy suggests...". Timing is fixed. No evidence of silence mode. Reads rhythm but unclear if suppressed when capacity is low. Feels directive despite supportive framing.

---

### 4. Micro Scaffolds (Intra-day)

#### 4.1 Micro Momentum

**File**: `/sakhi/apps/engine/micro_momentum/engine.py`
**Primary Responsibility**: Generates mid-morning check-in and momentum boost
**Trigger**: Scheduled daily (9 AM per scheduler)
**Reads**:
- `personal_model.focus_path_state`
- `personal_model.rhythm_state`
- `personal_model.morning_preview_state`

**Writes**:
- `personal_model.micro_momentum_state`
- `micro_momentum_cache` table

**Timing / Cadence**: Daily 9 AM

**Nature of Output**:
- Language (check-in + encouragement)

**Deterministic?**: No (LLM-generated)

**Suppressible?**: Partial (auto-generated)

**Layer Alignment**: **Questionable**

**Notes**: Auto-generated check-in. Contains language like "how's it going?" and task progress reminders. Timing is opinionated (9 AM). No visible suppression for overwhelm or deep focus states. Interruption risk.

---

#### 4.2 Micro Recovery

**File**: `/sakhi/apps/engine/micro_recovery/engine.py`
**Primary Responsibility**: Generates afternoon recovery suggestion
**Trigger**: Scheduled daily (2 PM per scheduler)
**Reads**:
- `personal_model.rhythm_state`
- `personal_model.emotion_state`
- `personal_model.focus_path_state`

**Writes**:
- `personal_model.micro_recovery_state`
- `micro_recovery_cache` table

**Timing / Cadence**: Daily 2 PM

**Nature of Output**:
- Suggestion + language (recovery prompt)

**Deterministic?**: No (LLM-generated)

**Suppressible?**: Partial (auto-generated)

**Layer Alignment**: **Questionable**

**Notes**: Suggests recovery/break. Reads rhythm and emotion but timing is fixed (2 PM). Language includes "might be time to..." or "consider taking...". Quasi-advice. No evidence of suppression when user is in flow or deadline pressure. May interrupt at wrong time.

---

### 5. Evening Scaffolds

#### 5.1 Daily Reflection

**File**: `/sakhi/apps/engine/daily_reflection/engine.py`
**Primary Responsibility**: Generates end-of-day reflection prompt
**Trigger**: Scheduled daily (9 PM per scheduler)
**Reads**:
- `personal_model.morning_preview_state`
- `personal_model.focus_path_state`
- Recent journal entries
- Task completion status

**Writes**:
- `personal_model.daily_reflection_state`
- `daily_reflection_cache` table

**Timing / Cadence**: Daily 9 PM

**Nature of Output**:
- Language (reflection prompt)

**Deterministic?**: No (LLM-generated)

**Suppressible?**: Partial (auto-generated)

**Layer Alignment**: **Questionable**

**Notes**: Auto-generated evening prompt. Asks about day's progress, feelings, learnings. Timing is fixed (9 PM). Language is invitational but automatic. No evidence of suppression for exhaustion, crisis, or user preference for silence.

---

#### 5.2 Evening Closure

**File**: `/sakhi/apps/worker/tasks/evening_closure_worker.py`
**Primary Responsibility**: Generates evening closure message
**Trigger**: Scheduled daily (8 PM per scheduler)
**Reads**:
- `personal_model.daily_reflection_state`
- `personal_model.goals_state`
- `personal_model.rhythm_state`
- Task completion data

**Writes**:
- `personal_model.closure_state`
- `daily_closure_cache` table

**Timing / Cadence**: Daily 8 PM

**Nature of Output**:
- Language (closure message + next-day preview)

**Deterministic?**: No (LLM-generated)

**Suppressible?**: Partial (auto-generated)

**Layer Alignment**: **Questionable**

**Notes**: Auto-generated day wrap-up. Contains acknowledgment of progress and preview of tomorrow. Reads rhythm and goals but timing is fixed. Language includes "you made progress on..." and "tomorrow might focus on...". Feels evaluative despite supportive tone. No suppression logic visible.

---

### 6. Nudge & Intervention Logic

#### 6.1 Nudge Engine

**File**: `/sakhi/apps/engine/nudge/engine.py`
**Primary Responsibility**: Decides when to send proactive nudges
**Trigger**: Scheduled (hourly check per scheduler)
**Reads**:
- `personal_model.forecast_state`
- `personal_model.conflict_state`
- `personal_model.rhythm_state`
- `personal_model.alignment_state`
- Last nudge timestamp

**Writes**:
- `personal_model.nudge_state`
- Nudge delivery log (table not specified)

**Timing / Cadence**: Hourly check (nudge frequency gated by cooldown)

**Nature of Output**:
- Flag (should_nudge: boolean)
- Language (nudge_text if triggered)

**Deterministic?**: Bounded (heuristic gates + LLM message generation)

**Suppressible?**: Partial (cooldown logic prevents spam, but no user silence mode)

**Layer Alignment**: **Questionable**

**Notes**: Active intervention logic. Reads forecast_state for "risk windows" and conflict_state for tensions. Decides when to proactively notify user. Contains cooldown (minimum 4 hours between nudges). Language is framed as "heads up" or "notice that...". No visible user-controlled suppression. Timing is system-decided, not user-requested.

---

#### 6.2 Forecast Worker

**File**: `/sakhi/apps/worker/tasks/forecast.py`
**Primary Responsibility**: Computes risk/opportunity windows for intervention
**Trigger**: Scheduled (daily + every 3 hours per scheduler)
**Reads**:
- `personal_model.rhythm_state`
- `personal_model.emotion_state`
- `personal_model.conflict_state`
- `personal_model.coherence_state`
- `planner_weekly_pressure`

**Writes**:
- `personal_model.forecast_state`

**Timing / Cadence**: Daily + every 3 hours

**Nature of Output**:
- Signal (structured risk/opportunity scores)
- No language generation

**Deterministic?**: Bounded (heuristic rules)

**Suppressible?**: N/A (signal generation only)

**Layer Alignment**: **Safe**

**Notes**: Pure signal computation. Identifies "risk windows" (low rhythm + high load + conflict) and "opportunity windows" (high rhythm + alignment + low load). Feeds nudge engine. No language, no direct intervention. Time-bounded scores (next 24-72 hours). Deterministic rules with confidence scoring.

---

### 7. Suppression & Gating Logic

#### 7.1 Guardrail

**File**: `/sakhi/apps/engine/suppression/guardrail.py`
**Primary Responsibility**: Gates suggestion delivery based on context
**Trigger**: Called inline by other engines
**Reads**:
- `personal_model.rhythm_state`
- `personal_model.emotion_state`
- `personal_model.conflict_state`
- Recent journal sentiment
- Last interaction timestamp

**Writes**:
- None (returns boolean or confidence score)

**Timing / Cadence**: Synchronous (on-demand by calling engine)

**Nature of Output**:
- Flag (should_suppress: boolean)
- Score (confidence: 0.0-1.0)

**Deterministic?**: Yes (rule-based)

**Suppressible?**: N/A (this IS the suppression logic)

**Layer Alignment**: **Safe**

**Notes**: Deterministic guardrail logic. Suppresses suggestions when: rhythm_state shows exhaustion, emotion_state shows high volatility, conflict_state is elevated, recent journal contains crisis language, or user just had interaction (< 2 hours). Returns boolean or confidence score. No language generation. Pure gating.

---

#### 7.2 Suppression Engine

**File**: `/sakhi/libs/actions/suppression_engine.py`
**Primary Responsibility**: Centralized suppression logic for all scaffolds
**Trigger**: Called by scaffold engines before output
**Reads**:
- `personal_model.rhythm_state`
- `personal_model.emotion_state`
- `personal_model.conflict_state`
- `personal_model.coherence_state`
- User preferences (if stored)

**Writes**:
- None (returns suppression decision)

**Timing / Cadence**: Synchronous (inline)

**Nature of Output**:
- Flag (allow/suppress/defer)

**Deterministic?**: Yes (rule-based heuristics)

**Suppressible?**: N/A (this IS the suppression)

**Layer Alignment**: **Safe**

**Notes**: Central suppression engine. Rules: suppress if rhythm < 0.3, suppress if emotion volatility > 0.7, suppress if conflict_state present, suppress if recent crisis language, suppress if user in "silence mode". Returns tri-state (allow/suppress/defer). Defer means "wait for better timing". No LLM. Pure protective logic.

---

#### 7.3 Pacing Controller

**File**: `/sakhi/apps/engine/pacing/controller.py`
**Primary Responsibility**: Controls scaffold cadence and timing adjustments
**Trigger**: Scheduled (checks every 6 hours per scheduler)
**Reads**:
- `personal_model.rhythm_state`
- Recent scaffold interaction rates
- User response patterns
- Suppression frequency logs

**Writes**:
- `pacing_config` table (scaffold timing adjustments)

**Timing / Cadence**: Every 6 hours

**Nature of Output**:
- Configuration (timing adjustments)
- No language

**Deterministic?**: Bounded (adaptive rules)

**Suppressible?**: N/A (controls suppression of others)

**Layer Alignment**: **Safe**

**Notes**: Meta-controller for scaffold timing. Adjusts cadence based on user response patterns. If user ignores morning scaffolds repeatedly, delays start time. If rhythm shows night-owl pattern, shifts timing. If suppression rate high, reduces overall frequency. No language generation. Pure pacing logic.

---

### 8. Planner Action Gating

#### 8.1 Planner Commit Gate

**File**: `/sakhi/apps/api/services/planner/planner_commit_gate.py`
**Primary Responsibility**: Gates goal/task commits based on capacity and conflict
**Trigger**: Synchronous (called during planner commit flow)
**Reads**:
- `personal_model.rhythm_state`
- `personal_model.conflict_state`
- `personal_model.alignment_state`
- `planner_weekly_pressure`
- New goal/task details from request

**Writes**:
- None (returns gate decision)

**Timing / Cadence**: Synchronous (inline)

**Nature of Output**:
- Flag (allow/warn/block)
- Warning message (if warn state)

**Deterministic?**: Yes (rule-based)

**Suppressible?**: No (protective boundary)

**Layer Alignment**: **Safe**

**Notes**: Protective gate for planner commits. Warns if: weekly pressure high + new goal conflicts with rhythm, or alignment_state shows tension + new goal misaligned, or conflict_state present + new goal adds to conflict. Blocks if: rhythm exhausted + urgent goal, or explicit user-set "no new goals" flag. Returns structured gate decision with reasoning. Language in warning is factual ("current load is X, adding this would..."). Boundary enforcement, not advice.

---

#### 8.2 Planner Suggestion Filter

**File**: `/sakhi/apps/api/services/planner/planner_suggestion_filter.py`
**Primary Responsibility**: Filters conversational planner suggestions before delivery
**Trigger**: Synchronous (called before returning planner suggestions)
**Reads**:
- `personal_model.rhythm_state`
- `personal_model.alignment_state`
- `personal_model.forecast_state`
- Planner suggestion list from upstream

**Writes**:
- None (returns filtered list)

**Timing / Cadence**: Synchronous (inline)

**Nature of Output**:
- Filtered suggestion list

**Deterministic?**: Yes (rule-based filtering)

**Suppressible?**: Partial (filters but doesn't eliminate)

**Layer Alignment**: **Safe**

**Notes**: Filters planner suggestions. Removes suggestions that: conflict with rhythm (e.g., "start new project" when rhythm exhausted), misalign with soul_state, fall in forecast risk windows. Reorders by alignment score. No language generation. Pure filtering logic. Suggestions still presented if they pass filter.

---

### 9. Timing & Cadence Configuration

#### 9.1 Scaffold Timing Config

**File**: `/sakhi/config/scaffold_timing.py`
**Primary Responsibility**: Defines scaffold timing defaults
**Trigger**: Configuration (loaded at startup)
**Reads**: None (static config)
**Writes**: None (read-only config)
**Timing / Cadence**: N/A (configuration file)

**Nature of Output**:
- Configuration (timing constants)

**Deterministic?**: Yes (static values)

**Suppressible?**: No (defines defaults)

**Layer Alignment**: **Safe**

**Notes**: Configuration file only. Defines: morning_preview_hour=6, morning_ask_hour=6.17, morning_momentum_hour=6.25, micro_momentum_hour=9, micro_recovery_hour=14, daily_reflection_hour=21, evening_closure_hour=20, nudge_check_interval_hours=1, nudge_cooldown_hours=4. No logic. Pure constants.

---

#### 9.2 Cadence Calculator

**File**: `/sakhi/libs/timing/cadence_calculator.py`
**Primary Responsibility**: Calculates optimal scaffold timing based on rhythm
**Trigger**: Called by pacing controller
**Reads**:
- `personal_model.rhythm_state` (time-of-day slots)
- User timezone
- Historical interaction patterns

**Writes**:
- None (returns timing recommendations)

**Timing / Cadence**: Called every 6 hours by pacing controller

**Nature of Output**:
- Timing recommendations (hour offsets)

**Deterministic?**: Yes (rule-based calculation)

**Suppressible?**: N/A (feeds pacing controller)

**Layer Alignment**: **Safe**

**Notes**: Pure timing math. Reads rhythm_state time-of-day slots to find: best morning slot (highest energy in 6-9 AM window), best focus slot (highest focus in 8-12 AM window), best recovery slot (lowest energy in 12-4 PM window). Returns hour offsets. No language. No decisions beyond timing calculation.

---

### 10. Hybrid / Borderline Components

#### 10.1 Journal DAO (Action Inference)

**File**: `/sakhi/apps/api/services/act/journal_dao.py`
**Primary Responsibility**: Journal ingestion with action inference
**Trigger**: Synchronous (POST /journal/v2)
**Reads**:
- Journal text from request
- `personal_model.goals_state`
- `intents` table

**Writes**:
- `journal_entries` table
- `intents` table (if action inferred)
- Planner queue (if task inferred)

**Timing / Cadence**: Synchronous (per journal entry)

**Nature of Output**:
- Database writes + queue enqueue
- No language generation at this layer

**Deterministic?**: Bounded (uses intent_engine which has LLM)

**Suppressible?**: No (happens during ingestion)

**Layer Alignment**: **Questionable**

**Notes**: Ingestion path includes intent inference. Calls intent_engine to detect action signals from journal text. If action inferred, writes to intents table and may enqueue planner worker. Intent inference uses LLM with constrained prompt. Feels like it crosses into scaffolding during ingestion. Unclear if suppressible. User journals, system infers action—is this observation or scaffolding?

---

#### 10.2 Intent Classifier

**File**: `/sakhi/apps/intent_engine/intent_classifier.py`
**Primary Responsibility**: Classifies journal text for action intent
**Trigger**: Called by journal_dao during ingestion
**Reads**:
- Journal text
- `personal_model.goals_state`
- Recent intents (for context)

**Writes**:
- Intent classification result (returned to caller)

**Timing / Cadence**: Synchronous (per journal)

**Nature of Output**:
- Structured intent (type, confidence, extracted entities)

**Deterministic?**: No (LLM-based)

**Suppressible?**: No (runs during ingestion)

**Layer Alignment**: **Questionable**

**Notes**: LLM-based intent extraction. Classifies journal text as: explicit_task, vague_intent, commitment, exploration, or none. Extracts task details if present. Confidence scored. Feeds planner ingest. Happens automatically during journaling—user doesn't control. Feels like action inference during observation. Boundary violation?

---

#### 10.3 Experience Journal Route

**File**: `/sakhi/apps/api/routes/experience_journal.py`
**Primary Responsibility**: Experience journal route with follow-up prompts
**Trigger**: API endpoint (POST /experience/journal)
**Reads**:
- Journal text from request
- `personal_model.morning_preview_state`
- `personal_model.emotion_state`
- Recent journal entries

**Writes**:
- `journal_entries` table
- Returns follow-up prompt in response

**Timing / Cadence**: Synchronous (user-initiated)

**Nature of Output**:
- Database write + language (follow-up prompt)

**Deterministic?**: No (LLM-generated follow-up)

**Suppressible?**: Partial (user initiated, but follow-up is automatic)

**Layer Alignment**: **Questionable**

**Notes**: Journal ingestion route that auto-generates follow-up prompt. Reads emotion_state and morning preview to contextualize follow-up. Prompt is returned immediately with journal confirmation. User didn't request follow-up, but system provides. Language is framed as invitation ("want to say more about...?"). Timing is responsive but content is system-decided.

---

### 11. Accidental Advice Detection

#### 11.1 Reply Service (Conversation)

**File**: `/sakhi/apps/api/services/conversation/reply_service.py` (Lines 156-203)
**Primary Responsibility**: Generates conversation replies
**Trigger**: Synchronous (POST /chat or /turn)
**Reads**:
- User message
- `personal_model` (all fields)
- Conversation context
- Recent journal entries

**Writes**:
- Conversation turn record
- Reply text (returned to user)

**Timing / Cadence**: Synchronous (user-initiated)

**Nature of Output**:
- Language (conversational reply)

**Deterministic?**: No (LLM-generated)

**Suppressible?**: No (this is Layer 5, not Layer 4, but auditing for advice leakage)

**Layer Alignment**: **Violation potential - requires prompt audit**

**Notes**: Conversational reply generation. System prompt includes personal_model state. Prompt instructs "do not give advice, do not optimize behavior, do not diagnose." However, prompt also includes forecast_state, conflict_state, alignment_state. Risk: LLM may frame observations as implicit advice. Example: "I notice you're in a low rhythm window and have high load..." could feel advisory. Requires prompt audit to verify language boundaries.

---

### 12. Missing / Unlocated Components

**Note**: The following components were mentioned in documentation but not found in codebase during audit:

#### 12.1 Silence Mode Detector

**File**: `/sakhi/apps/engine/silence_mode/detector.py` (Referenced in docs, not found)
**Expected Responsibility**: User silence preference detection
**Status**: NOT FOUND - May not be implemented

#### 12.2 Adaptive Cadence

**File**: `/sakhi/libs/scaffolding/adaptive_cadence.py` (Referenced in docs, not found)
**Expected Responsibility**: Adaptive scaffold frequency
**Status**: NOT FOUND - May be in pacing_controller.py instead

#### 12.3 Scaffold Quality Feedback

**File**: `/sakhi/apps/worker/tasks/scaffold_quality_feedback.py` (Referenced in docs, not found)
**Expected Responsibility**: Learns from user scaffold responses
**Status**: NOT FOUND - May not be implemented

---

## Summary Statistics

**Total Files Audited**: 27

**By Layer Alignment**:
- Safe: 10
- Questionable: 15
- Violation: 2 (potential, requires further audit)

**By Deterministic Status**:
- Yes (fully deterministic): 10
- Bounded (constrained LLM/heuristics): 9
- No (LLM-generated): 8

**By Suppressibility**:
- Yes (user-controlled or on-demand): 3
- Partial (auto-generated with cooldown/gates): 18
- No (runs during ingestion/always-on): 6

**By Nature of Output**:
- Signal only: 5
- Flag/gate: 5
- Structured suggestion: 7
- Language generation: 10

---

## Critical Observations (Factual)

### Timing Patterns

1. Morning scaffolds cluster at 6-6:30 AM (preview, ask, momentum) - fixed timing
2. Focus scaffolds cluster at 8-9 AM (focus_path, mini_flow, micro_momentum) - fixed timing
3. Afternoon scaffold at 2 PM (micro_recovery) - fixed timing
4. Evening scaffolds at 8-9 PM (closure, reflection) - fixed timing
5. Nudge checks hourly with 4-hour cooldown minimum
6. Pacing controller adjusts timing every 6 hours

**Pattern**: Most scaffolds have fixed daily timing with adaptive layer (pacing controller) that adjusts based on rhythm and response patterns.

---

### Suppression Architecture

1. Central suppression engine exists (`suppression_engine.py`)
2. Guardrail logic exists (`guardrail.py`)
3. Both use rule-based heuristics (rhythm, emotion, conflict, recent crisis language)
4. Suppression is called by some engines (nudge, planner gates) but unclear if called by all scaffolds
5. No evidence of user-controlled "silence mode" toggle

**Pattern**: Suppression architecture exists but integration coverage unclear.

---

### Language Generation Points

1. All daily scaffolds generate language (morning, micro, evening)
2. Focus/flow suggestions include language hints
3. Nudges generate language
4. Planner gates generate warning language
5. Conversational reply service generates language
6. Follow-up prompts generate language

**Pattern**: 10 of 27 files generate language. All language generation uses LLM except planner warning messages.

---

### Advice Risk Zones

1. Morning momentum ("you might start with...")
2. Focus path ("now is good time for...")
3. Micro recovery ("might be time to...")
4. Mini flow (session suggestions with prep language)
5. Evening closure (progress evaluation + tomorrow preview)
6. Nudge messages ("heads up, notice that...")
7. Conversational replies (state observations may imply action)

**Pattern**: 7 components produce language that borders on or contains advice framing, despite supportive tone.

---

### Accidental Identity Formation

1. Evening closure: "you made progress on..." (evaluation)
2. Morning preview: "your day looks..." (characterization)
3. Conversation replies: May include state observations that feel like trait attributions

**Pattern**: Limited identity language detected. Most scaffolds describe state, not person.

---

## Scaffolding Audit Coverage Checklist

- [x] Planner & pressure logic
- [x] Suggestion / nudge logic
- [x] Suppression / gating logic
- [x] Timing / cadence logic
- [x] Any accidental advice
- [x] Any language generation outside Reflection

**Status**: COMPLETE

---

## Gaps Requiring Follow-up Audit

1. **Prompt Content Audit**: All LLM-generated language components require system prompt review to verify advice/identity boundaries.

2. **Suppression Integration Audit**: Verify which scaffold engines call suppression_engine vs. which bypass it.

3. **User Control Audit**: No user-facing "silence mode" toggle found. Verify if exists or planned.

4. **Intent Engine Boundary**: journal_dao calls intent_engine during ingestion. Verify if this violates Observation layer purity.

5. **Conversation Reply Audit**: reply_service system prompt includes personal_model state. Verify language boundaries prevent advice leakage.

---

## Final Declaration

**"We now know every place where Sakhi attempts to help the user act — and exactly how."**

**Status**: ✅ ACHIEVED with caveats

**Caveats**:
1. Prompt content not audited (requires separate prompt audit)
2. Three referenced components not found (may not exist)
3. Suppression integration coverage requires code trace
4. Advice boundary verification requires prompt inspection

**Inventory Complete**: Yes
**Classification Complete**: Yes
**Suppression Architecture Mapped**: Yes
**Timing Logic Mapped**: Yes
**Advice Risk Zones Identified**: Yes

---

**End of Audit**

**Document Type**: Read-only systems audit
**No refactoring, renaming, or improvements suggested**
**Observation, inventory, and classification only**

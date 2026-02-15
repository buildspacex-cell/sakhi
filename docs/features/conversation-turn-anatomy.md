# Anatomy of a Conversation Turn

> **A single document tracing the full lifecycle of a `POST /v2/turn` request — from HTTP entry to background worker completion.**
>
> Source of truth. All other pipeline docs (`adaptive-response.md`, `pipeline-deep-dive.md`, `context-routing.md`) are supplements.
>
> Last Updated: 2026-02-11

---

## Overview

When a user sends a message, 12 things happen synchronously (in the HTTP request) and 3 things happen asynchronously (background workers). The reply typically arrives in 1–3 seconds. Background workers continue for another 5–15 seconds after the response is sent.

```
User message
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  SYNCHRONOUS (in-request, ~1-3s)                        │
│                                                         │
│  1. Session Management                                  │
│  2. Vision Processing (if image attached)               │
│  3. Agentic Tools (web search if factual question)      │
│  4. Journal Orchestration (entry_id, embedding, topics) │
│  5. Brain State Load (personal_model)                   │
│  6. Context Router (which modules to activate)          │
│  7. Tier 1: Fast Context Scan (always, ~10ms)           │
│  8. Tier 2: Deep Context (router-gated, ~50-200ms)      │
│  9. Friction State + Recommendations                    │
│  10. Adaptive Pipeline (5 stages, ~100ms)               │
│  11. LLM Call (conversation engine, ~500-2000ms)        │
│  12. Persistence + Worker Dispatch                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
  │
  ▼  HTTP response returned
  │
┌─────────────────────────────────────────────────────────┐
│  ASYNCHRONOUS (background workers, ~5-15s)              │
│                                                         │
│  A. turn_memory_update  (captures turn to memory)       │
│  B. episodic_consolidation_v21  (episodes + vectors)    │
│  C. preference_learning  ("I like..." statements)       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Walkthrough

### Step 1: Session Management

**File:** `routes/turn_v2.py:356-399`

The turn starts by resolving the user and ensuring a conversation session exists:

```
POST /v2/turn  { text: "my nose has been blocked for two days" }
  │
  ├─ resolve_person(request)  →  person_id
  ├─ ensure_session(person_id, slug="converse")  →  session_id
  └─ load_context_with_summary(session_id)
       ├─ recent_turns: last 8 turns (verbatim)
       ├─ session_summary: compressed older context
       └─ total_turns: count for compression trigger
```

**Session compression**: When `total_turns >= 16` and no summary exists, older turns are compressed into a semantic summary with markers for pronouns, topics, and emotional threads. This keeps the LLM context window manageable while preserving references ("she" → "partner mentioned earlier").

**Data flows to:** `conversation_history` and `session_summary` in metadata_payload → conversation engine.

---

### Step 2: Vision Processing (conditional)

**File:** `routes/turn_v2.py:402-498`

Only runs if `image_data` or `media_ids` are present in the request.

```
image_data (base64)
  │
  ├─ store_media()  →  media_record (persisted)
  ├─ process_image()  →  description, objects, tags, text
  ├─ update_media_analysis()
  ├─ learn_from_image()  →  memory facts from visual content
  └─ add_to_visual_context(session_id)
```

**Data flows to:** `vision_context` in metadata_payload.

---

### Step 3: Agentic Tools (conditional)

**File:** `routes/turn_v2.py:499-592`

Auto-detects if the message needs external information (factual questions, "search for...", "look up...") but NOT personal questions ("I feel...").

```
"what is the latest research on turmeric benefits"
  │
  ├─ Trigger detection: "latest" + not personal  →  needs_search=True
  ├─ web_search(query, max_results=5)
  └─ summarize_search_results()  →  agentic_context.web_search
```

**Data flows to:** `agentic_context` in metadata_payload.

---

### Step 4: Journal Orchestration

**File:** `routes/turn_v2.py:597-620`

Every turn goes through the journal orchestrator which creates a journal entry, generates embeddings, extracts topics, and detects intents.

```
orchestrate_turn(person_id, text)
  │
  ├─ journal_entries  →  entry_id (UUID)
  ├─ journal_embeddings  →  embedding (1536-dim vector)
  ├─ extract_topics()  →  topics: ["congestion", "health"]
  ├─ extract_emotion()  →  emotion: {label: "concerned", score: 0.7}
  └─ detect_intents()  →  intents: ["seek_help"]
```

**Data flows to:** `entry_id`, `topics`, `emotion`, `stored_intents` — used by context router and metadata.

---

### Step 5: Brain State Load

**File:** `routes/turn_v2.py:699-708`

Loads the user's persistent state from `personal_model`:

```
_get_brain_state_from_personal_model(person_id)
  │
  ├─ operating_system    (Ayurvedic constitution / OS type)
  ├─ emotion_state       (current emotional profile)
  ├─ soul_state          (values, narrative, shadow)
  ├─ rhythm_state        (daily rhythm patterns)
  ├─ longitudinal_state  (long-term trajectory)
  └─ identity_momentum_state  (growth direction)
```

Also loads `internal_state` from `load_internal_state()`:
- `dosha_baseline`, `operating_system`, `life_context`, `decision_profile`
- `cognitive_load`, `priority`, `soul_values`, `soul_identity`, `life_themes`

**Data flows to:** All Tier 1 computations and metadata_payload.

---

### Step 6: Context Router

**File:** `services/context_router.py`

**Purpose:** Determine which expensive context modules to activate for this specific message. This is the key performance optimization — without it, every turn would run all 13 modules.

```
route_context(text, intents, topics, emotion, hour, has_image)
  │
  ├─ Deterministic classifier (keyword matching, ~0ms)
  │   └─ confidence >= 0.5?  →  use deterministic result
  │
  └─ LLM fallback (fast model, ~100ms)
      └─ confidence < 0.5?  →  ask LLM which modules apply
```

**13 Available Modules:**

| Module | What it gates | Cost |
|--------|--------------|------|
| `identity` | Narrative, alignment, momentum, timeline deep context | Medium (DB reads) |
| `emotional_depth` | Inner dialogue, nudge state (LLM calls) | High |
| `moment` | Evidence pack, deliberation scaffold | High |
| `recommendations` | Personalized Ayurvedic recommendations | Medium (DB + computation) |
| `scheduling` | Calendar, relationship nudges, Sakhi Mesh | Medium (DB reads) |
| `email` | Email context, contact preferences | Medium (DB reads) |
| `causal` | Causal reasoning — "why am I feeling X" (LLM) | High |
| `morning_ritual` | Morning preview, ask, momentum | Low (cache reads) |
| `evening_ritual` | Evening closure | Low (cache read) |
| `micro_flow` | Focus path, mini flow, micro journey | Low-Medium |
| `reflection` | Daily reflection | Low (cache read) |
| `vision` | Image processing | High |
| `agentic` | Web search, agent tasks | High (external APIs) |
| `body` | Health data, symptoms, HealthKit | Medium |

**Keyword tables drive deterministic routing:**
- "email", "inbox" → `email`
- "schedule", "calendar" → `scheduling`
- "why am i", "what's causing" → `causal`
- "i feel", "overwhelmed", "anxious" → `emotional_depth`
- "sleep", "headache", "tired" → `body`
- etc.

**Data flows to:** `active_modules` set — gates all Tier 2 computations.

---

### Step 7: Tier 1 — Fast Context Scan (always runs)

**File:** `routes/turn_v2.py:743-772`, `conversation_reasoner.py:14-143`

These are cheap, synchronous computations that always run. Their outputs feed a compact "360° Context Scan" that's always present in the LLM prompt.

```
Tier 1 computations (~10ms total):
  ├─ compute_fast_narrative()         →  dominant_theme, emotional_trend
  ├─ compute_alignment()             →  alignment_score, conflict_zones
  ├─ compute_fast_rhythm_soul_frame()  →  coherence_score, rhythm_tone
  ├─ compute_fast_esr_frame()        →  emotion-soul-rhythm snapshot
  ├─ compute_fast_identity_momentum()  →  momentum_direction, score
  ├─ compute_fast_identity_timeline() →  current_phase, emerging_signal
  ├─ compute_microreg()              →  shift, amplitude, risk
  ├─ compute_tone()                  →  tone state
  └─ compute_empathy()               →  empathy pattern
```

These are compressed into a single-line-per-module scan:

```
[CONTEXT SCAN — 360° awareness, use as background intelligence]
Identity: momentum=growing, score=0.7, alignment=0.8, phase=integration, narrative=self-discovery
Emotional: empathy=mirroring, microreg=steady, amplitude=0.3, risk=low
Moment: mode=companion, load=moderate, energy=steady, need=validation
Friction: Mild Friction (drift=18%)
Body: sleep=fair, 6.2h, hrv=42, energy=moderate
```

**Data flows to:** `metadata_payload` → `build_context_scan()` in conversation_reasoner.

---

### Step 8: Tier 2 — Deep Context (router-gated)

**File:** `routes/turn_v2.py:773-1320`, `conversation_reasoner.py:150+`

Only the modules activated by the context router (Step 6) run here. Each produces a detailed prompt section.

**Example: "emotional_depth" module active:**
```
[EMOTIONAL STATE — Deep Context]
Inner dialogue: The part that needs rest is arguing with the part that pushes forward
Empathy: mirroring their uncertainty
Microreg: slight downward shift (amplitude=0.4, risk=moderate)

Guidance: Hold space for both sides. Don't rush to fix.
Mirror their language. Validate before redirecting.
```

**Example: "body" module active:**
```
[BODY & PHYSICAL STATE]
Sleep: fair quality, 6.2h (below your usual 7.5h)
Heart rate variability: 42ms (trending down over 2 weeks)
Energy: moderate
Sleep trend: declining

Your body data suggests: sleep quality is worth paying attention to.
```

**Key Tier 2 blocks:**

| Module | What runs | Output |
|--------|-----------|--------|
| `emotional_depth` | `compute_inner_dialogue()` (LLM), nudge_state (DB) | Inner dialogue, nudge guidance |
| `moment` | `select_evidence_anchors()`, `compute_deliberation_scaffold()` | Evidence-based decision support |
| `body` | `compute_health_trends(14 days)` | Longitudinal health trends |
| `causal` | `explain_friction_state()` or `explain_symptom()` (LLM) | Root cause analysis |
| `email` | `get_email_context_for_conversation()` | Email digest, contact preferences |
| `scheduling` | Calendar queries, relationship nudges, Sakhi Mesh checks | Scheduling options |
| `morning_ritual` | Cache reads: preview, ask, momentum | Morning context |
| `evening_ritual` | Cache read: closure | Evening wind-down context |

**Data flows to:** `metadata_payload` → conversation_reasoner builds Tier 2 prompt sections.

---

### Step 9: Friction State + Recommendations

**File:** `routes/turn_v2.py:1113-1220`

Always computed (independent of router). The friction state is the user's current deviation from their natural constitution.

```
Friction State Computation:
  ├─ compute_current_vikriti(person_id)  →  present-state dosha levels
  ├─ compute_baseline_drift(prakruti, vikriti)  →  drift_percentage
  └─ classify_friction_state(drift)  →  state, description
```

**Friction states (jargon-free names):**

| Internal | User-facing | Drift | Meaning |
|----------|-------------|-------|---------|
| vata imbalance | Chaos | >15% vata | Scattered, anxious, overwhelmed |
| pitta imbalance | Intensity | >15% pitta | Pushing too hard, burning out |
| kapha imbalance | Stagnation | >15% kapha | Stuck, heavy, unmotivated |
| balanced | Balanced | <15% | Equilibrium |

**Recommendation triggers:**

| Trigger | Condition |
|---------|-----------|
| Reactive | User explicitly asks ("what should I do", "help me") |
| Proactive | Drift > 25% — high friction |
| Contextual | Morning (before 10am) or evening (after 7pm) |
| Nudge | Drift 15-25% — gentle suggestion |
| Body | Body module active (symptom detected) |

When triggered, `build_recommendation_context()` and `generate_personalized_recommendations()` produce foods, practices, and immediate actions.

**Data flows to:** `friction_state_computed`, `personalized_recommendations` in metadata_payload.

---

### Step 10: Adaptive Response Pipeline (5 stages)

**File:** `services/response/pipeline.py`, `conversation_engine.py:96-121`

This is the intelligence layer that makes Sakhi's replies contextual rather than generic. It runs in parallel with the base prompt system. If all 5 stages succeed, the adaptive prompt replaces the base prompt.

```
run_adaptive_pipeline(person_id, user_text, session_id)
  │
  ├─ Stage 1: SENSING  (sync, ~1ms)
  │   └─ sense_message(text)
  │       → domain: "body"
  │       → symptom: "congestion"
  │       → temporal: "acute" (two days)
  │       → tone: "matter-of-fact"
  │       → specificity: "medium"
  │       → urgency: "moderate"
  │       → confidence: 0.85
  │
  ├─ Stage 2: KNOWLEDGE GAP  (async, ~50ms)
  │   └─ analyze_knowledge_gap(person_id, sense)
  │       → constitution: {dominant_dosha: "kapha", os: "Conservation"}
  │       → known: ["has had congestion before", "prefers warm drinks"]
  │       → inferred: ["likely kapha aggravation given season"]
  │       → unknown: ["has this happened before?", "any other symptoms?"]
  │
  ├─ Stage 3: STRATEGY  (sync, ~1ms)
  │   └─ select_response_strategy(sense, gap)
  │       → mode: "CONNECT_AND_INQUIRE" or "RESPOND" or "INQUIRE"
  │       → questions_to_ask: (max 2, from diagnostic questions)
  │       → known_to_reference: (don't re-ask what we know)
  │       → reasoning: "medium specificity + known constitution → connect then ask"
  │
  ├─ Stage 4: SYNTHESIS  (sync, ~5ms)
  │   └─ synthesize_context(sense, gap, strategy, ...)
  │       → Jargon-free context (OS name, friction description, recommendations)
  │       → Life context, known facts, symptom characteristics
  │       → Response guidance (tone, causes, avoid list)
  │       → Body state translated to friendly language
  │
  └─ Stage 5: PROMPT FORMATION  (sync, ~1ms)
      └─ build_adaptive_prompt(user_text, synthesized)
          → Final prompt string (see Prompt Template below)
```

**Response Modes:**

| Mode | When | Behavior |
|------|------|----------|
| `RESPOND` | High specificity + enough known context | Direct recommendation, reference what we know |
| `CONNECT_AND_INQUIRE` | Medium specificity | Acknowledge → share insight → ask 1-2 questions |
| `INQUIRE` | Low specificity, many unknowns | Empathize → ask targeted diagnostic questions |

**Data flows to:** `adaptive_prompt` string → conversation engine selects this over base prompt.

---

### Step 11: LLM Call (Conversation Engine)

**File:** `services/conversation_v2/conversation_engine.py`

This is where the actual reply is generated. The conversation engine assembles the final messages array and calls the LLM.

```
generate_reply(person_id, user_text, metadata, session_id)
  │
  ├─ build_conversation_context(person_id)  →  memory, patterns, mind state
  ├─ decide_tone(context, behavior_profile)  →  tone blueprint
  ├─ generate_journaling_guidance()  →  journaling prompts
  │
  ├─ should_use_adaptive_pipeline()?
  │   ├─ YES → run_adaptive_pipeline()  →  adaptive_prompt
  │   └─ NO  → build_prompt() (base prompt from conversation_reasoner)
  │
  ├─ build_recall_context()  →  relevant memories (BM25 + vector)
  ├─ build_patterns_context()  →  detected patterns
  │
  └─ call_llm(messages)
```

**Messages array structure:**

```
messages = [
  { role: "system", content: recall_context + patterns_context },
  { role: "system", content: adaptive_prompt OR base_prompt },
  { role: "system", content: "[Earlier Conversation Context]\n" + session_summary },  // if available
  { role: "user",   content: "turn 3 message" },    // from conversation_history
  { role: "assistant", content: "turn 3 reply" },   // from conversation_history
  { role: "user",   content: "turn 4 message" },
  { role: "assistant", content: "turn 4 reply" },
  ...up to 8 recent turns...
  { role: "user",   content: "my nose has been blocked for two days" },  // current message
]
```

**Two prompt systems compete:**

| System | Source | When it wins |
|--------|--------|-------------|
| **Adaptive prompt** | `build_adaptive_prompt()` in synthesizer.py | All 5 pipeline stages succeed |
| **Base prompt** | `build_prompt()` in conversation_reasoner.py | Adaptive pipeline fails or is disabled |

The adaptive prompt is richer — it includes OS type, friction state, symptom protocol, recommendations, life context, memory graph relationships, and body state all formatted into a structured prompt template.

**Model:** `gpt-4o-mini` by default (env: `MODEL_CONVERSATION`).

---

### Step 12: Persistence + Worker Dispatch

**File:** `routes/turn_v2.py:1862-2249`

After the reply is generated:

```
Post-reply (sync):
  ├─ append_turn(role="user", text=body.text)      // persist user turn
  ├─ append_turn(role="assistant", text=reply)      // persist reply
  ├─ _write_turn_memory(dialog_state, reasoning)    // dialog state to memory
  ├─ update_continuity(emotion, tone, empathy)      // session continuity
  ├─ update_conversation_topics(text)               // topic tracking
  ├─ update_session_persona(text)                   // persona tuning
  ├─ publish(MEMORY_EVENT)                          // event bus
  └─ ingest_heavy(entry_id, text)                   // async task: heavy memory processing

Worker dispatch:
  └─ enqueue_turn_jobs(turn_id, person_id, jobs, payload)
      ├─ turn_memory_update
      ├─ episodic_consolidation_v21
      └─ preference_learning
```

**Data returned to client:**

```json
{
  "reply": "Two days of congestion — that sounds uncomfortable...",
  "sessionId": "uuid",
  "tone": "gentle, steady",
  "friction_state": { "state": "Mild Friction", "drift_percentage": 18 },
  "personalized_recommendations": { "foods": [...], "practices": [...] },
  "adaptive_response": { "sense": {...}, "strategy": {...}, ... },
  "journaling_ai": { "prompt": "What does this congestion feel like beyond physical?" },
  ...40+ other context fields...
}
```

---

## Background Workers (Async)

**File:** `services/turn/async_triggers.py`, `apps/worker/`

Three workers run after every turn. They don't affect the reply — they update the user's model for future turns.

### A. `turn_memory_update`

Captures the turn into the memory system:
- Stores text + reply in `memory_short_term`
- Updates facts in `memory_facts` (BM25 searchable)
- Extracts entities for the memory graph

### B. `episodic_consolidation_v21`

Creates episodic memory from accumulated turns:
- Groups recent turns into "episodes" (coherent conversation segments)
- Generates state vectors for each episode
- Updates `memory_episodic` with summaries
- Feeds the memory graph with cross-entity relationships

### C. `preference_learning`

Learns user preferences from statements like "I like...", "I prefer...", "I don't want...":
- Extracts preference signals
- Updates `user_preferences` table
- Feeds into recommendation personalization

### Daily Scheduled Workers (not per-turn)

These heavier computations run on a daily schedule, not per turn:

| Worker | Schedule | What it does |
|--------|----------|-------------|
| `ayurvedic_pipeline` | Daily 6am | Recompute vikriti, refresh dosha vectors |
| `rhythm_forecast` | Daily 7am | Predict daily rhythm, best times for activities |
| `identity_momentum_deep` | Daily 6am | Deep identity trajectory analysis |
| `emotion_soul_rhythm_deep` | Daily 4am | Deep emotional pattern analysis |
| `soul_refresh` | Daily 6am | Update soul state (values, shadow, narrative) |
| `longitudinal_update` | Weekly | Long-term trajectory and phase detection |

---

## The Adaptive Prompt Template

**File:** `services/response/synthesizer.py:611-772`

This is the actual prompt template sent to the LLM when the adaptive pipeline succeeds. Every `{variable}` is filled in by the synthesis stage.

```
You are Sakhi — a friend who really gets this person. You understand their patterns.

VOICE: Talk like a friend. Not a therapist, not formal. Just real.
- Simple words. Short sentences. Say what matters.
- No Ayurvedic jargon ever (vata, pitta, kapha, dosha = never say these).
- Warm but direct. Skip fluff.

───────────────────────────────────────────────────────────────────
THEM: {os_name} — {constitution_description}
───────────────────────────────────────────────────────────────────
{os_description}

Right now: {friction_state} ({drift_description})
{friction_description}

{friction_quick_reframe}

Watch for: {body_signals_to_watch}
Energy: {energy_mode_name} — {energy_mode_description}

───────────────────────────────────────────────────────────────────
THEIR LIFE
───────────────────────────────────────────────────────────────────
- {life_context items: people, work, concerns, location}

{body_state_section — if health data available}

───────────────────────────────────────────────────────────────────
CONNECTIONS (things pulling in different directions or supporting each other)
───────────────────────────────────────────────────────────────────
- {memory graph relationships — competing and supporting entities}

───────────────────────────────────────────────────────────────────
WHAT WE KNOW (don't ask again)
───────────────────────────────────────────────────────────────────
- {known facts from memory}
- {inferences from current state}

───────────────────────────────────────────────────────────────────
WHAT THEY'RE TALKING ABOUT
───────────────────────────────────────────────────────────────────
Area: {domain}
About: {symptom}
Pattern: {temporal}
{symptom_characteristics}

───────────────────────────────────────────────────────────────────
HOW TO RESPOND: {response_mode}
───────────────────────────────────────────────────────────────────
{decision_reasoning — why this mode was chosen}

Tone: {tone_guidance}
{likely_causes}
{questions_to_ask — if INQUIRY/CONNECT_AND_INQUIRE mode}
{avoid_suggesting}

───────────────────────────────────────────────────────────────────
WHAT COULD HELP
───────────────────────────────────────────────────────────────────
{symptom_insight — OS-aware explanation of why this symptom for this person}
  → {best_food.what} — {best_food.why}
  → {best_practice.what} — {best_practice.why}
Skip: {avoid items}

OR (fallback when no symptom protocol):

{what_helps_now — friction-state general guidance}
Quick things:
  → {immediate_actions}
Good to eat: {foods}
Try: {practices}

───────────────────────────────────────────────────────────────────
RULES
───────────────────────────────────────────────────────────────────
• Talk like a friend, not a therapist or doctor. Simple words.
• NEVER use Ayurvedic terms or clinical language.
• Be warm, direct, real. Skip the filler words.
• Pick the 1-2 most likely things, don't list options.
• Max 2 questions. Make them feel natural, not like an interview.
• If we already know something, reference it — don't re-ask.
• No diagnosis. You're a friend, not a doctor.
• Keep it short. 30-50 words usually. Say what matters.

{template_guidance — mode-specific response template}

───────────────────────────────────────────────────────────────────
THEY SAID:
───────────────────────────────────────────────────────────────────
{user_text}

───────────────────────────────────────────────────────────────────
YOUR RESPONSE (like a friend would say it — warm, simple, real):
───────────────────────────────────────────────────────────────────
```

---

## The Jargon-Free Translation Layer

**File:** `services/response/translation.py`

All Ayurvedic/yogic terminology is translated before reaching the LLM. The science stays — the Sanskrit transforms.

| Internal (Ayurvedic) | User-facing (jargon-free) |
|----------------------|--------------------------|
| Vata-dominant | "Adaptive" (quick-moving, creative) |
| Pitta-dominant | "Performance" (driven, focused) |
| Kapha-dominant | "Conservation" (steady, grounded) |
| Tridoshic | "Balanced" |
| Vata imbalance | "Chaos" — scattered energy |
| Pitta imbalance | "Intensity" — running too hot |
| Kapha imbalance | "Stagnation" — stuck energy |
| Sattva | "Clear" — balanced energy |
| Rajas | "Active" — driven energy |
| Tamas | "Heavy" — low energy |
| Drift percentage | How far from your natural baseline |
| Prakruti | "Your natural pattern" |
| Vikriti | "Where you are right now" |
| Dosha | "System type" or "pattern" |

**OS Types (constitution → personality framework):**

| Dosha combo | OS Name | Description |
|-------------|---------|-------------|
| Vata primary | Adaptive | Quick-moving mind, creative energy, flexible |
| Pitta primary | Performance | Driven, focused, results-oriented |
| Kapha primary | Conservation | Steady, grounded, methodical |
| Vata-Pitta | Adaptive-Performance | Creative intensity |
| Pitta-Kapha | Performance-Conservation | Focused stability |
| Vata-Kapha | Adaptive-Conservation | Creative grounding |
| Balanced | Balanced | Even distribution |

---

## Data Flow Summary

```
                    ┌──────────────────────────┐
                    │     personal_model        │
                    │  (persisted user state)   │
                    └───────┬──────────────────┘
                            │ brain_state, internal_state
                            ▼
user_text ──────► [Context Router] ──► active_modules
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         Tier 1 (all)   Tier 2 (gated)  Adaptive Pipeline
         ~10ms          ~50-200ms       ~100ms
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                    metadata_payload
                    (40+ context fields)
                            │
                            ▼
                ┌───────────────────────┐
                │  conversation_engine  │
                │  generate_reply()     │
                ├───────────────────────┤
                │ System: recall + patterns
                │ System: adaptive_prompt OR base_prompt
                │ System: session_summary
                │ User/Assistant: conversation_history (8 turns)
                │ User: current message
                └───────────┬───────────┘
                            │
                            ▼
                    call_llm(messages)
                    MODEL: gpt-4o-mini
                            │
                            ▼
                    reply_text (30-50 words)
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         append_turn    dispatch workers  return response
         (persist)      (async)           (to client)
```

---

## Key Design Decisions

### 1. Two Prompt Systems (Adaptive vs Base)

The adaptive pipeline produces a richer, more structured prompt. But it can fail (missing constitution data, sensing error). The base prompt from `conversation_reasoner.py` always works as a fallback. The conversation engine tries adaptive first.

### 2. Router-Gated Context (Tier 1 / Tier 2)

Not every message needs every module. "What's for dinner?" doesn't need emotional depth analysis. The context router keeps latency low by only running expensive modules when relevant.

### 3. Session Compression (Hybrid Memory)

Recent turns are kept verbatim (8 turns). Older turns are compressed into semantic summaries with pronoun resolution markers. This gives the LLM both immediate context and long-term awareness.

### 4. Per-Turn vs Daily Workers

Heavy state recomputation (vikriti vectors, rhythm forecasts, identity momentum) moved to daily schedules. Per-turn workers only do essential memory capture. This cut turn latency significantly.

### 5. Jargon-Free by Design

The LLM never sees Ayurvedic terminology. All translation happens before prompt assembly. This prevents the LLM from leaking Sanskrit terms into responses.

### 6. Guardrails in Prompt

Every prompt includes explicit guardrails:
- Talk like a friend, not a therapist
- Never use Ayurvedic terms
- Keep it short (30-50 words)
- Max 2 questions
- No diagnosis

---

## File Reference

| File | Role |
|------|------|
| `routes/turn_v2.py` | HTTP handler — orchestrates everything (~2200 lines) |
| `services/conversation_v2/conversation_engine.py` | Assembles messages, calls LLM (~250 lines) |
| `services/conversation_v2/conversation_reasoner.py` | Base prompt builder + Tier 1/2 sections (~500 lines) |
| `services/context_router.py` | Keyword + LLM router for module activation (~250 lines) |
| `services/response/pipeline.py` | Adaptive pipeline orchestrator — 5 stages (~400 lines) |
| `services/response/sensing.py` | Stage 1: Message classification |
| `services/response/knowledge_gap.py` | Stage 2: Memory query + gap identification |
| `services/response/strategy.py` | Stage 3: Response mode selection |
| `services/response/synthesizer.py` | Stage 4 + 5: Context synthesis + prompt formation (~800 lines) |
| `services/response/translation.py` | Jargon-free translation layer |
| `services/response/diagnostic_kb.py` | Symptom → dosha mapping, OS insight templates |
| `services/recommendations/context_builder.py` | Recommendation context (constitution, state, patterns) |
| `services/memory/sessions.py` | Session management, turn persistence, compression |
| `services/memory/recall.py` | BM25 + vector memory retrieval |
| `services/turn/async_triggers.py` | Worker dispatch |
| `services/turn/deterministic_context_loader.py` | Shared context loading |
| `apps/worker/pipelines/turn_updates/runner.py` | Background worker runner |

---

## Example: Complete Turn Trace

**User says:** "my nose has been blocked for two days"

```
1. Session: session_id=abc123, 4 prior turns loaded, no summary yet
2. Vision: skipped (no image)
3. Agentic: skipped (personal message, not factual query)
4. Journal: entry_id=xyz789, topics=["congestion","health"], emotion=concerned
5. Brain: os=Conservation, dosha_baseline={kapha:0.45, pitta:0.30, vata:0.25}
6. Router: active_modules = {body, recommendations, causal}
7. Tier 1: friction=Mild Friction (18%), momentum=stable, empathy=mirroring
8. Tier 2: health_trends (sleep declining), causal_explanation (kapha+season)
9. Friction: drift=18%, trigger=reactive (body module active)
   Recs: warm ginger water, steam inhalation, avoid dairy
10. Adaptive Pipeline:
    - Sense: domain=body, symptom=congestion, temporal=acute, specificity=medium
    - Gap: known=["prefers warm drinks"], unknown=["other symptoms?"]
    - Strategy: CONNECT_AND_INQUIRE (medium specificity)
    - Synthesis: OS=Conservation, friction=Mild Friction, tone=warm+grounding
    - Prompt: Full adaptive prompt with symptom protocol
11. LLM: gpt-4o-mini → "Two days of congestion — that sounds heavy..."
12. Persist: turns saved, workers dispatched

Workers (async):
  A. turn_memory_update: stores "congestion for 2 days" as memory fact
  B. episodic_consolidation: groups with recent health-related turns
  C. preference_learning: no preference signal detected
```

**Reply:** "Two days of congestion — that sounds uncomfortable. Your system tends to hold on to heaviness, especially this time of year. Warm ginger water might help cut through it. Is there anything else going on — any tiredness or heaviness?"

---

## Changelog

- **2026-02-11 (Hardening Sprint)**:
  - **P0**: Strategy decision tree now has Case 1b — established users (known ≥ 2 or inferred ≥ 2) with medium specificity get RESPOND mode (help directly) instead of CONNECT_AND_INQUIRE. New users still get assessment questions.
  - **P1**: Response payload split into product fields (10 fields: reply, adaptive_response, memory_recall, etc.) and debug_data (22 fields). Debug gated by `SAKHI_DEBUG_RESPONSE=1` env var or `?debug=1` query param.
  - **P2**: Base prompt voice aligned with adaptive: "a friend who really gets this person" instead of "emotionally intelligent clarity companion". Ayurvedic jargon stripped from all prompt sections.
  - **P5**: Context router LLM fallback fixed (was importing from non-existent module).
  - **P6**: Legacy `/chat` and `/llm` endpoints re-prefixed to `/dev/chat` and `/dev/llm`.

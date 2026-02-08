# Context Router — Tiered Context Intelligence

> Intelligent context module selection for conversation turns. 360-degree awareness with focused detail.

---

## Overview

The Context Router solves a core problem: `turn_v2.py` computes ~60 metadata fields every turn, but the LLM prompt only used ~20 of them. ~40 fields (identity frames, inner dialogue, moment model, evidence pack, morning/evening rituals, micro flow) were computed but never reached the prompt.

**Approach: Context Tiering**
- **Tier 1 (always)**: Lightweight 1-2 line summary of EVERY module — the LLM always has 360-degree awareness
- **Tier 2 (router-gated)**: Full detailed sections only for modules the router selects as relevant

This ensures the LLM never misses relevant context (e.g., identity momentum can matter even when the user says "I feel stuck") while keeping the prompt focused and computation costs low.

---

## Architecture

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  HYBRID ROUTER                                                   │
│  1. Deterministic keyword/pattern classifier (~0ms)             │
│  2. Intent-based routing from extracted intents                 │
│  3. Time-based routing (morning 5-11, evening 20+)             │
│  4. Structural triggers (has_image, has_pending_task)           │
│  5. LLM fallback (GPT-4o-mini) when confidence < 0.5           │
│  Output: Set of active module names + confidence score          │
└─────────────────────────────────────────────────────────────────┘
     │
     ├── active_modules: {"emotional_depth", "identity"}
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: 360° Context Scan (always in prompt)                    │
│                                                                  │
│  [CONTEXT SCAN — 360° awareness, use as background intelligence] │
│  Identity: momentum building (0.72), alignment 0.84, phase: ...  │
│  Emotional: empathy=mirror, microreg=grounding, risk: low        │
│  Moment: mode=companion, load=moderate, energy=stable            │
│  Friction: intensity (drift: 18%)                                │
│  Morning: focus on deep work, 3 tasks                            │
│  Micro: momentum nudge active                                    │
│                                                                  │
│  5-10 lines max. Omits modules with no data.                     │
│  Source: cheap pure functions + DB cache reads (~0ms)             │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: Deep Context Sections (only for active modules)         │
│                                                                  │
│  [IDENTITY & GROWTH — Deep Context]                              │
│  Narrative: transformation, trend: ascending, shadow: ...        │
│  Values alignment: 0.84 — conflicts: work-life                   │
│  Identity momentum: 0.72 (building), drag: 0.15                  │
│  ...                                                             │
│  Guidance: Reflect their narrative arc. Acknowledge growth...    │
│                                                                  │
│  [EMOTIONAL ATTUNEMENT — Deep Context]                           │
│  Inner voice: grounding (tone: warm)                             │
│  ...                                                             │
│                                                                  │
│  Source: LLM calls, DB queries, only when router activates       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 13 Context Modules

| Module | What it covers | Tier 1 cost | Tier 2 cost |
|--------|---------------|-------------|-------------|
| `identity` | Narrative trace, alignment, rhythm soul, identity momentum, timeline | Pure functions (~0ms) | Already in tier 1 |
| `emotional_depth` | Inner dialogue, empathy state, microreg state, nudge state | DB side effects (always run) | Inner dialogue (LLM call) |
| `moment` | Moment model, evidence pack, deliberation scaffold | Pure function (~0ms) | Evidence pack (DB + LLM) |
| `recommendations` | Friction state, personalized recommendations | Classification (cheap) | Recommendation generation (LLM) |
| `scheduling` | Calendar, scheduling intent, relationship nudges | — | DB queries + intent detection |
| `email` | Email context, contact preferences | — | DB reads |
| `causal` | Causal reasoning (why am I feeling X) | — | Explain friction (LLM call) |
| `morning_ritual` | Morning preview, morning ask, morning momentum | Cache reads (cheap) | Already in tier 1 |
| `evening_ritual` | Evening closure | Cache reads (cheap) | Already in tier 1 |
| `micro_flow` | Micro momentum, recovery, focus path, mini flow, journey | Cache reads (cheap) | Generation (LLM, only on trigger) |
| `reflection` | Daily reflection | Cache reads (cheap) | Already in tier 1 |
| `vision` | Image processing | — | Vision pipeline |
| `agentic` | Web search, agent tasks | — | Search + task processing |

---

## Routing Rules

### Deterministic Classifier

| Module | Triggered by |
|--------|-------------|
| `email` | "email", "inbox", "mail", "messages", "unread" |
| `scheduling` | "schedule", "calendar", "meeting", "book", "when am i free", "plan my day/week" |
| `recommendations` | "recommend", "suggest", "help me", "what should i", "feeling off", "out of balance" |
| `causal` | "why am i", "why do i feel", "what's causing", "why is my" |
| `identity` | "who am i", "who i am", "my values", "my purpose", "identity", "growth", "becoming" |
| `emotional_depth` | "i feel", "overwhelmed", "anxious", "scared", "need support", "lonely", "stressed" |
| `moment` | "decision", "crossroads", "should i", "choice", "torn between", "dilemma" |
| `micro_flow` | "focus", "stuck", "momentum", "flow", "next step", "what now", "where do i start" |
| `reflection` | "reflect", "how was my day", "journal", "look back", "what did i learn" |
| `agentic` | "search for", "look up", "find out", "research", "google", "browse" |
| `morning_ritual` | Hour 5-11 |
| `evening_ritual` | Hour >= 20 |
| `vision` | Image attached |

### Intent-Based Routing

Intents extracted from the message (by the upstream NLU) also trigger modules:
- `schedule_*` or `calendar_*` intents → `scheduling`
- `email_*` or `inbox_*` intents → `email`
- `health_*` or `ayurved*` or `dosha_*` intents → `recommendations` + `causal`
- `identity_*` or `purpose_*` or `growth_*` intents → `identity`
- `decision_*` or `choice_*` intents → `moment`

### LLM Fallback

When the deterministic classifier has low confidence (< 0.5), a fast GPT-4o-mini call classifies which modules are relevant. This handles messages like "I've been thinking a lot about things lately" that don't match keywords but may need emotional_depth or identity context.

### Override Rules

Some modules activate regardless of routing when critical thresholds are met:
- `recommendations` activates when `drift_percentage > 25%`
- `causal` activates when `drift_percentage > 15%`

---

## Examples

| User Message | Context Scan (always) | Tier 2 Deep Sections |
|---|---|---|
| "Hey" | Full scan | (none) — lean response |
| "Good morning!" | Full scan | Morning ritual detail |
| "How's my inbox?" | Full scan | Email detail |
| "Why am I feeling scattered?" | Full scan | Causal + Recommendations |
| "Who am I becoming?" | Full scan | Identity deep context |
| "I'm overwhelmed and scared" | Full scan (shows empathy=mirror, microreg=grounding) | Emotional depth (inner dialogue, empathy, nudges) |
| "Should I take this job?" | Full scan (shows momentum, alignment, tension) | Moment + Identity detail |
| "I feel stuck" | Full scan (reveals momentum stalled, alignment dropping) | Micro flow + (LLM may add emotional_depth) |

---

## Files

| File | Purpose |
|------|---------|
| `sakhi/apps/api/services/context_router.py` | Hybrid router: deterministic classifier + LLM fallback |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | `build_context_scan()` (tier 1) + `build_tier2_section()` (tier 2) |
| `sakhi/apps/api/routes/turn_v2.py` | Router integration: calls router, gates expensive computations |
| `sakhi/tests/unit/services/test_context_router.py` | 32 tests for router |
| `sakhi/tests/unit/services/test_conversation_reasoner.py` | 39 tests including context scan + tier 2 sections |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Tier 1 scan always present | LLM can connect dots across modules even when not the primary topic |
| DB side-effect computations always run | microreg + empathy write to personal_model; must always compute |
| Hybrid deterministic + LLM | Keywords catch 80%+ of cases at ~0ms; LLM handles the ambiguous 20% |
| `_SkipModule` exception pattern | Gates large try/except blocks in turn_v2.py without re-indenting 200+ lines |
| Override thresholds for drift | Safety net: high friction drift always triggers causal/recommendations regardless of routing |

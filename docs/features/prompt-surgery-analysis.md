# Prompt Surgery — MVP Simplification Analysis

> **Date:** 2026-03-05
> **Scope:** All three conversation modes — Normal Chat, Deep Answer, Topic Reflection
> **Thesis:** Continuity is the MVP value, not Ayurveda. Strip everything that isn't continuity or safety.

---

## Executive Summary

The normal chat prompt assembles **15 blocks** into a ~2000-3000 token system prompt. The continuity section — the actual differentiator — is one block buried in the middle, surrounded by raw JSON blobs, Ayurveda framing, and rarely-populated feature sections. The "lost in the middle" problem applies: the LLM sees noise before and after the signal.

**Recommendation:** Strip to continuity + safety. Each mode gets exactly the context it needs — no more.

### The Three Modes — What Each Actually Needs

| | Normal Chat | Deep Answer | Topic Reflection |
|---|-------------|-------------|------------------|
| **Purpose** | Respond to what the user just said | Answer a specific question with full history as lens | Reflect on the whole story of a topic |
| **Topic continuity** | Last 7-8 entries on this topic | The whole arc — origin, pivots, current stage, all evidence | Everything we have on this topic |
| **Conversation context** | Last 2-3 turns (may be different topics — user might reference recent cross-topic context) | Last 2-3 turns (same reason — "you said X about Y" needs cross-topic awareness) | Not needed — no current question, purely longitudinal |
| **Current query** | Yes — the user's message | Yes — the user's question | No — there is no question, it's a whole-topic reflection |
| **Depth of history** | Shallow — recent entries + arc summary | Deep — full arc, all phases, all evidence anchors | Deep — full arc, all phases, all evidence anchors |
| **Word budget** | 60-120 words | 150-250 words | 80-140 words |

**Key insight:** Normal chat needs *recent* continuity + conversation context. Deep answer needs *full* continuity + conversation context. Topic reflection needs *full* continuity only — no conversation context, no current query.

### Design Principles

1. **Strip to continuity + safety for MVP.** Scheduling, email, vision, recommendations, Ayurveda — all cut from the prompt. They go into a pending actions list for post-MVP.
2. **Keep machine-readable metadata for system/debug** but stop injecting raw JSON into LLM text. Enriched context and behavior cues stay in the debug payload, not in the prompt.
3. **Deep mode = more depth, not more rigidity.** The deep answer should feel like a friend who took time to think, not a therapist filling out a form.
4. **Continuity is the only signal.** Everything else is post-MVP.
5. **Conversation context is not the same as topic continuity.** The last 2-3 turns give the LLM awareness of what was just discussed (which may be a different topic). Topic continuity gives it the longitudinal story. Both are needed in chat and deep answer modes, but not in topic reflection.

---

## Mode 1: Normal Chat

**File:** `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py:897-936`

### Block-by-Block Analysis

| # | Block | Lines | What It Does | Tokens | MVP Verdict |
|---|-------|-------|-------------|--------|-------------|
| 1 | **Voice directive** | 897-903 | "You are Sakhi — a friend who really gets this person" + voice rules (simple words, no jargon, warm but direct) | ~60 | **KEEP** — core identity |
| 2 | **Tone/Emotion/Energy** | 905-909 | `tone_style`, `pace`, `last_emotion`, `energy_level`, `mirroring` strategy, active `themes` | ~40 | **SIMPLIFY** — keep tone_style + emotion. Drop mirroring strategy, pace, themes (over-cuing) |
| 3 | **Conversation context** | 911-912 | Last 2-3 conversation turns (may span different topics) | ~80 | **KEEP** — essential. User might say "like I said about work" while talking about sleep. Cross-topic references need this |
| 4 | **Enriched context JSON** | 914-915 | Raw JSON: topics, emotion_hint, intents, plans, rhythm_trigger, meta_reflection_trigger, behavior_profile | ~200 | **STOP INJECTING** — keep in debug payload, not in LLM text. Raw JSON is not useful prompt content |
| 5 | **Behavior cues JSON** | 916-917 | Raw behavior_profile JSON dump | ~100 | **STOP INJECTING** — keep in debug payload. Duplicate of enriched_context field |
| 6 | **Journal section** | 918 | Journaling AI cues | ~40 | **REMOVE** — rarely populated, adds noise |
| 7 | **Recommendation section** | 558-566 | Personalized recommendations: trigger type, quick actions, foods, practices | ~150 | **CUT** — Ayurveda-heavy. Post-MVP |
| 8 | **Scheduling section** | 589-713 | Calendar context: events, relationship nudges, time suggestions, confirmation flows | ~200 | **CUT** — separate feature. Post-MVP |
| 9 | **Context scan (360°)** | 100-125 | One-liners: identity, emotional, moment, micro flow, friction, body | ~120 | **SIMPLIFY** — keep friction state + emotion. Drop body/micro/identity (duplicated in Tier 2, rarely useful) |
| 10 | **Continuity section** | 803-830 | `[LONGITUDINAL CONTINUITY]`: topic label, arc_compact (start/pivots/current), phase_block, anchor_block, qualitative_summary, decision_ledger, evidence_block | ~500-800 | **KEEP — crown jewel.** For normal chat: last 7-8 entries on this topic + arc summary. Full arc data available but scoped to recent window |
| 11 | **Operating System section** | 494-503 | Conservation/Expansion type + dosha baseline + strengths/vulnerabilities | ~80 | **REMOVE for MVP** — Ayurveda framing, not continuity |
| 12 | **Governance section** | 506-509 | Constitutional AI guard directive | ~50 | **KEEP** — safety-critical |
| 13 | **Tier 2 deep sections** | 144-382 | 5 router-gated subsections: identity, emotional depth, moment intelligence, micro flow, body/physical | ~300 | **REMOVE for MVP** — 5 complex subsections, most never populated. Over-engineers the prompt |
| 14 | **Email + Causal + Vision** | 841-895 | Email intelligence patterns, dosha-based causal reasoning ("why you feel this way"), image descriptions | ~200 | **CUT** — all three are separate features or Ayurveda framing. Post-MVP |
| 15 | **Response guidelines** | 932-935 | "60-120 words, lead with practical help, max 1 question, confirm before scheduling" | ~40 | **KEEP** — essential guardrail |

### Token Budget

| | Current | MVP |
|---|---------|-----|
| Total prompt tokens (est.) | 2000-3000 | 800-1200 |
| Continuity signal ratio | ~25% | ~60% |
| Blocks | 15 | 5 |

### Block Disposition

| Block | MVP Status | Post-MVP Action |
|-------|------------|-----------------|
| Enriched context JSON | **Debug only** — stays in `metadata_payload` for turn debug panel | Intent-gate: inject relevant fields when specific intents detected |
| Behavior cues JSON | **Debug only** — machine-readable, not prompt content | Same |
| Recommendations | **Cut** — not in prompt | Re-add as intent-gated block when recommendation_trigger fires |
| Scheduling | **Cut** — not in prompt | Re-add as intent-gated block when scheduling_intent detected |
| Email intelligence | **Cut** — not in prompt | Re-add as intent-gated block when user asks about inbox |
| Vision context | **Cut** — not in prompt | Re-add as intent-gated block when image shared |
| Tier 2 sections | **Cut** — not in prompt | Re-add per-module when router activates them |
| Operating System | **Cut** — not in prompt | Re-add for Ayurvedic personalization layer |
| Causal reasoning | **Debug only** — stays in metadata | Re-add when continuity + Ayurveda integration is ready |
| Journal cues | **Removed** — rarely populated | Unlikely to return |

**Key principle:** MVP prompt = continuity + safety. Everything else is cut and tracked in Pending Actions for post-MVP.

---

## Mode 2: Deep Answer

**File:** `sakhi/apps/api/services/continuity/reflection.py`

### System Prompt (lines 42-46)

```
You are Sakhi - a friend who gets this person deeply.
Speak naturally, warm and direct. Keep it grounded in the packet evidence.
Do not use therapy-speak or Ayurvedic jargon.
Do not introduce themes that are not explicitly present in the packet.
Follow the response contract exactly.
```

**Verdict: KEEP — already clean and focused.**

### User Prompt Structure (lines 914-931)

| # | Block | What It Does | Verdict |
|---|-------|-------------|---------|
| 1 | Instruction header | "Write one deep reflection reply... Stay within topic... Answer query first..." | **KEEP** |
| 2 | `Mode: deep_answer` | Tells LLM which format to use | **KEEP** |
| 3 | `Current query source` | "provided" / "topic_turn_recovery" / "none" | **REMOVE** — internal metadata, LLM doesn't need to know *how* the query was sourced |
| 4 | **Full topic history** | Topic, origin story, current stage, key shifts, story flow (all phases), recurring tensions, open questions, all episodes, all evidence anchors | **KEEP — the whole arc, not just recent entries. This is what makes it "deep"** |
| 5 | **Conversation context** | Last 2-3 turns (may be cross-topic) | **ADD** — currently missing. User might say "you said X about Y" referencing a recent turn on another topic. Deep answer needs this bridge |
| 6 | **Person lines** | Stable pattern, ongoing tension, state hints (emotion, load, energy, identity phase), delta since last reflection | **SIMPLIFY** — emotion hint useful. Load/energy/identity phase are noise for a deep answer |
| 7 | **Current query** | The actual user question | **KEEP** |
| 8 | **Response contract** | Voice, length, format, sections, avoid list, detail/mirror/nudge policy | **SIMPLIFY** (see below) |

### Response Contract Problem (lines 492-514)

Current deep answer contract requires **5 labeled sections**:

1. Direct answer
2. History anchors
3. Recommended path
4. Alternative path
5. Risk + next 7-day action

Plus a quality gate (lines 994-1014) that checks for these exact labels and triggers a **revision loop** if any are missing.

**The problem isn't the depth — it's the rigidity.**

Deep mode should mean: "I took more time to think about your question. I went deeper into your history. I gave you a more thoughtful, grounded answer."

Deep mode should NOT mean: "I filled out 5 labeled sections in a structured form."

A "friend who gets you deeply" does not say:

> **History anchors:** Two weeks ago you mentioned...
> **Alternative path:** You could also consider...
> **Risk + next 7-day action:** The risk is...

The rigid format fights the voice. It produces output that reads like a therapist's treatment plan, not a friend's insight. The quality gate then enforces this rigidity — rejecting perfectly good answers because they didn't include a label called "Alternative path."

**What deep should actually mean:**

| | Normal Chat | Deep Answer |
|---|-------------|-------------|
| **Words** | 60-120 | 150-250 |
| **Topic history** | Last 7-8 entries on this topic | Full arc — origin, all phases, all pivots, all evidence |
| **Conversation context** | Last 2-3 turns (cross-topic) | Last 2-3 turns (cross-topic) |
| **History references** | 0-1 past moments | 2-3 past moments naturally woven in |
| **Closing** | One practical next step | One practical suggestion + one honest question |
| **Continuity role** | Background signal | Foreground narrative — the depth comes from more history, not more structure |

**MVP contract:**

```
- 150-250 words
- Answer the question directly, with their full history as your lens
- Weave in 2-3 specific past moments naturally — don't label them, reference them like a friend would
- End with one practical suggestion and one honest question
- Write as one flowing response, no section headers
```

This eliminates:
- The quality gate check (lines 994-1014)
- The revision prompt (lines 1017-1030)
- The `_has_required_section` matching logic (lines 1033-1050)
- One extra LLM call per deep answer (the revision loop)

**Simplification: ~80 lines of code removed. One fewer LLM round-trip.**

### Arc Compact Global (lines 549-571)

The `_build_arc_compact_global()` function produces:

| Field | What It Is | Verdict |
|-------|-----------|---------|
| `origin_story` | Where this topic began | **KEEP** |
| `key_pivots` (max 3) | Major shifts | **KEEP** |
| `current_stage` | Where it is now | **KEEP** |
| `recurring_tensions` (max 3) | Patterns that keep returning | **KEEP** |
| `open_questions` (max 2) | Unresolved questions | **KEEP** |
| `phase_compaction` | Condensed phase timeline | **KEEP** |

**This structure is already excellent.** It's the right data for the right purpose.

---

## Mode 3: Topic Reflection

**File:** `sakhi/apps/api/services/continuity/reflection.py:515-525`

### What makes this mode different

Topic reflection has **no current question** and **no conversation context**. It's purely longitudinal — "tell me the whole story of this topic." The LLM gets the full arc and nothing else.

This means:
- No conversation turns injected (the user isn't asking something — the system is reflecting)
- No user message in the prompt
- Full topic arc with all phases, pivots, evidence
- Output is a concise reflection, not an answer

### Current contract

```python
{
    "voice": "friend, warm, direct",
    "length_words": "80-140",
    "format": "single short paragraph",
    "priority": "longitudinal_reflection",
}
```

Plus guidance: "highlight what changed, what repeats, and one question to carry forward."

**Verdict: Already clean.** The 80-140 word single paragraph format is right. The guidance is the right framing.

**Trim:**
- Remove `detail_allowed` / `mirror_allowed` / `nudge_policy` from the contract. Gate at code level: if topic doesn't meet threshold, don't call reflection at all.
- Remove conversation context loading from this mode's pipeline — it's wasted work since the prompt doesn't use it.

---

## Continuity Pack Builder

**File:** `sakhi/apps/api/services/continuity/chat.py:53-143`

This builds the data that feeds the `[LONGITUDINAL CONTINUITY]` section in normal chat.

| Field | What It Is | Verdict |
|-------|-----------|---------|
| `topic_key` / `topic_label` | Classified topic from user text | **KEEP** |
| `arc_compact` (start/pivots/current signals) | Arc narrative compressed to 3 signals | **KEEP — core** |
| `history_compact.phase_path` | Phase timeline entries | **KEEP** |
| `history_compact.anchor_points` | Key moments from journal | **KEEP** |
| `history_compact.qualitative_arc_summary` | Prose summary of the arc | **KEEP** — gives the model narrative context |
| `history_compact.qualitative_mode` | "mirror_only" vs "grounded_mirror" | **REMOVE from prompt** — internal policy label |
| `history_compact.decision_ledger` | Past decisions + accepted Sakhi suggestions | **KEEP** — prevents repeating resolved suggestions |
| `evidence` | Selected journal snippets with timestamps | **KEEP** |
| `surface` (classification/coherence scores) | Gating metadata | **REMOVE from prompt** — keep in code for gating decisions, don't inject into LLM context |

**The pack itself is well-designed.** The problem isn't the continuity data — it's the 14 other blocks drowning it out.

---

## The Core Problem

The continuity section is the most differentiated signal in the prompt. But in the current architecture:

```
[Voice]                    ← 60 tokens
[Tone/Emotion/Energy]      ← 40 tokens
[STM]                      ← 80 tokens
[Raw JSON blob]            ← 200 tokens   ← CUT (debug-only)
[More raw JSON]            ← 100 tokens   ← CUT (debug-only)
[Journal cues]             ← 40 tokens    ← CUT
[Recommendations]          ← 150 tokens   ← CUT (post-MVP)
[Scheduling]               ← 200 tokens   ← CUT (post-MVP)
[Context scan]             ← 120 tokens   ← SIMPLIFY (keep emotion + friction only)
[CONTINUITY]               ← 500-800 tokens ← THE VALUE
[Operating System]         ← 80 tokens    ← CUT (post-MVP)
[Governance]               ← 50 tokens
[Tier 2 sections]          ← 300 tokens   ← CUT (post-MVP)
[Email/Causal/Vision]      ← 200 tokens   ← CUT (post-MVP)
[Response rules]           ← 40 tokens
```

The continuity signal sits at position ~990/2160 tokens — literally the middle. Research on "lost in the middle" shows LLMs attend weakest to information in the center of the context.

For MVP: cut everything that isn't continuity or safety. Track cut features in Pending Actions for post-MVP re-integration.

---

## MVP Prompt Architecture

### Normal Chat

```
[Voice]                    ← 60 tokens   — who you are, how you talk
[Emotion + Friction]       ← 30 tokens   — current emotional/friction state
[Conversation context]     ← 80 tokens   — last 2-3 turns (any topic — cross-topic awareness)
[TOPIC CONTINUITY]         ← 400-600 tokens — last 7-8 entries on this topic + arc summary + decisions
[Governance guard]         ← 50 tokens   — if present
[User message]
[Response rules]           ← 40 tokens   — 60-120 words, practical, max 1 question
```

**Total: ~700-900 tokens.** The LLM knows what was just discussed (conversation context) AND the recent thread on this topic (continuity). If the user says "like I mentioned about work" while talking about sleep, the conversation context provides that bridge.

### Deep Answer

```
[Voice]                    ← 60 tokens   — same voice directive
[Emotion]                  ← 20 tokens   — current emotional state
[Conversation context]     ← 80 tokens   — last 2-3 turns (cross-topic awareness)
[FULL TOPIC ARC]           ← 800-1200 tokens — origin, all phases, all pivots, all evidence, full story
[Current query]
[Response contract]        ← 60 tokens   — 150-250 words, weave in history, one suggestion + one question
```

**Total: ~1100-1500 tokens.** Same conversation context as chat (user might reference recent cross-topic exchanges), but the topic continuity is the *full arc* — not just last 7-8 entries. This is what makes it "deep." More history, not more rigid structure.

### Topic Reflection

```
[Voice]                    ← 60 tokens   — same voice directive
[FULL TOPIC ARC]           ← 800-1200 tokens — origin, all phases, all pivots, all evidence, full story
[Response contract]        ← 40 tokens   — 80-140 words, what changed, what repeats, one question
```

**Total: ~900-1300 tokens.** No conversation context — this isn't about a current question. No user message. Purely longitudinal: "tell me the whole story of this topic." The LLM's only job is to reflect on the full arc.

### Context layering across modes

```
                    Conversation context    Topic continuity depth    Current query
                    (last 2-3 turns)        (how much history)        (user's question)
                    ─────────────────       ──────────────────────    ──────────────────
Normal Chat         ✓ (cross-topic)         Shallow (7-8 entries)     ✓
Deep Answer         ✓ (cross-topic)         Full arc (all entries)    ✓
Topic Reflection    ✗                       Full arc (all entries)    ✗
```

---

## Implementation Plan

### Phase 1: Strip Normal Chat Prompt

**File:** `conversation_reasoner.py:build_prompt()`

1. **Cut from prompt assembly:** enriched_context JSON, behavior_cues JSON, journal_section, recommendation_section, scheduling_section, os_section, tier2_sections, email_section, causal_section, vision_section.
2. **Simplify context scan** — keep only emotion + friction from the 360° scan. Drop body/micro/identity one-liners.
3. **Scope topic continuity** — last 7-8 entries on the classified topic + arc summary + decision ledger. Not the full arc.
4. **Keep conversation context** — last 2-3 turns (any topic) for cross-topic reference awareness.
5. **Reorder** — Voice → Emotion/Friction → Conversation context → Topic continuity → Governance → User → Rules.
6. **Keep metadata intact** — all cut data stays in `metadata_payload` for the debug panel. No data loss, just no prompt injection.

**Impact:** Prompt drops from ~2500 to ~700-900 tokens. Code for cut sections stays in the file (commented or behind a `False` guard) for post-MVP.

### Phase 2: Restructure Deep Answer

**File:** `reflection.py`

1. **Feed the full topic arc** — origin, all phases, all pivots, all evidence, full story. This is what makes it "deep" — more history, not more structure.
2. **Add conversation context** — last 2-3 turns (cross-topic) so the LLM understands recent conversational references. Currently missing from deep answer pipeline.
3. Replace 5-section rigid contract with natural prose contract: "150-250 words, weave in 2-3 past moments naturally, end with one suggestion + one question, no section headers."
4. Remove quality gate (`_passes_deep_answer_quality_gate`) — no more label checking.
5. Remove revision prompt (`_build_deep_answer_revision_prompt`) — no more retry loop.
6. Remove `_has_required_section` matcher.
7. Simplify person_lines: keep emotion hint, drop load/energy/identity phase.

**Impact:** ~80 lines removed, one fewer LLM call per deep answer. Deep answers are deeper (full arc) and more natural (no rigid sections).

### Phase 3: Trim Topic Reflection

**File:** `reflection.py`

1. Remove `detail_allowed` / `mirror_allowed` / `nudge_policy` from contract.
2. Gate at code level: if topic doesn't meet threshold, don't call reflection at all.
3. **Remove conversation context loading** — topic reflection is purely longitudinal. No current question, no recent turns. Wasted work to load them.
4. Feed the full topic arc (same depth as deep answer).

**Impact:** ~10 lines simplified. Pipeline becomes cleaner — no unnecessary DB queries for conversation turns.

### Phase 4: Clean Continuity Pack

**File:** `conversation_reasoner.py` (lines 718-830) + `chat.py` (lines 53-143)

1. Remove `qualitative_mode` from prompt text (internal policy label).
2. Remove `surface` scores from prompt text (gating metadata, not LLM-useful).
3. **Add entry-count scoping** — for normal chat, limit evidence to last 7-8 entries on this topic. For deep answer / topic reflection, use full evidence set.
4. Keep: topic, arc_compact, phase_block, anchor_block, qualitative_summary, decision_ledger, evidence_block.

**Impact:** Continuity pack becomes mode-aware — shallow for chat, deep for reflection modes.

---

## What This Means for the Product

### Before (current prompt)
The LLM gets: "Here's everything we know about this person — their dosha, their sleep, their email patterns, their identity momentum, their micro flow scaffolds, their body state, their calendar, their causal reasoning, oh and also here's their continuity arc on this topic."

The model tries to be everything. Results are scattered.

### After (MVP prompt)
Three modes, each with exactly the context it needs:

**Normal chat:** "Here's what they said in the last few turns. Here's the recent thread on this topic — the last 7-8 entries, the arc summary, decisions they've made. Now respond to what they just said."

**Deep answer:** "Here's what they said recently. Here's the *full story* of this topic — where it started, every phase, every pivot, every key moment in their own words. Now answer their question with all of that as your lens."

**Topic reflection:** "Here's the full story of this topic. No question to answer. Just reflect — what changed, what keeps coming back, what's still unresolved."

### The business pitch changes from:
"We have 30 engines that compute your identity momentum, micro flow, body dosha, emotional attunement..."

### To:
"We remember what you've been going through. When you say 'I'm stressed about work again,' we know this started 22 days ago, pivoted when you got feedback from your manager, and keeps coming back every Monday. Our response is grounded in *your* story, not generic advice. And when you ask us to go deeper, we don't just give a longer answer — we use your *full history* on that topic."

That's the pitch. Continuity is the moat. The three modes are three zoom levels on the same data — recent thread, full story, pure reflection.

---

## Pending Actions (Post-MVP)

Features cut from MVP prompt. Re-integrate when ready.

| Feature | What It Did | Re-integration Approach | Priority |
|---------|------------|------------------------|----------|
| **Scheduling context** | Calendar events, time suggestions, relationship nudges, confirmation flows | Intent-gate: inject only when `scheduling_intent` detected (create/query/block/find_time) | High — users will ask about calendar |
| **Email intelligence** | Email patterns, avoidance signals, cognitive load | Intent-gate: inject only when user asks about inbox | Medium |
| **Vision context** | Image descriptions, extracted text | Intent-gate: inject only when image shared in current turn | Medium |
| **Recommendations** | Ayurvedic foods, practices, quick actions based on friction state | Intent-gate: inject when `recommendation_trigger` fires (reactive/proactive/contextual) | Low — requires Ayurveda integration decision |
| **Operating System** | Conservation/Expansion type, dosha baseline, strengths/vulnerabilities | Decide whether to keep Ayurvedic framing or reframe as behavioral personality type | Low |
| **Tier 2 deep sections** | Identity, emotional depth, moment intelligence, micro flow, body/physical | Re-enable per-module via router when engines are reliably populated | Low |
| **Causal reasoning** | Dosha-based "why you feel this way" explanation | Reframe: use continuity arc to explain patterns through user's own history instead of dosha lens | Low |
| **Enriched context JSON** | Raw topics, intents, plans, triggers | Intent-gate: extract specific fields when relevant intent detected instead of dumping entire JSON | Low |

---

## Files Referenced

| File | Lines | Purpose |
|------|-------|---------|
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | 897-936 | Main chat prompt assembly |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | 100-125 | Context scan (360°) |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | 144-382 | Tier 2 deep sections |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | 494-503 | Operating system section |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | 558-566 | Recommendations section |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | 589-713 | Scheduling section |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | 718-830 | Continuity section builder |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | 841-895 | Email + causal + vision |
| `sakhi/apps/api/services/continuity/reflection.py` | 42-46 | Deep reflection system prompt |
| `sakhi/apps/api/services/continuity/reflection.py` | 492-528 | Response contracts (deep answer + topic reflection) |
| `sakhi/apps/api/services/continuity/reflection.py` | 789-935 | Prompt message assembly |
| `sakhi/apps/api/services/continuity/reflection.py` | 994-1030 | Quality gate + revision loop |
| `sakhi/apps/api/services/continuity/reflection.py` | 549-571 | Arc compact global builder |
| `sakhi/apps/api/services/continuity/chat.py` | 53-143 | Continuity pack builder |
| `sakhi/apps/api/services/continuity/chat.py` | 275-304 | History compact builder |
| `sakhi/apps/api/services/continuity/chat.py` | 341-378 | Decision ledger builder |
| `sakhi/apps/api/services/continuity/chat.py` | 431-478 | Qualitative arc summary |

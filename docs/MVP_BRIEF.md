# Sakhi MVP — Product & Engine Brief

> March 2026 · Internal reference

---

## Positioning

Sakhi is a personal AI that remembers the arc of your life, not just your last message.

Most AI is stateless — it knows what you said five minutes ago, nothing more. Sakhi holds a longitudinal model of who you are: your recurring tensions, the decisions you keep circling, the patterns that show up across work, relationships, and health. It reads the thread behind what you're saying, not just the words.

The surface is a conversation. The engine is continuity.

---

## What We Shipped (MVP)

### Two surfaces, one engine

**Sakhi (the frontend)**
A conversation app on mobile (iOS) and web. The MVP runtime is deliberately narrow:

- Auth → name-only onboarding → conversation
- Returning users land directly in conversation
- Text-first. No voice, no HealthKit, no soul-screen extras in the live flow

**Kala (the engine)**
A deterministic governance and continuity kernel. It runs underneath every conversation, invisible to the user. It ensures Sakhi's behavior is consistent, auditable, and earned — it will not surface a pattern until there is enough evidence; it will not repeat a suggestion the person has already rejected.

---

## The Continuity Engine

This is the core product bet. Everything else is context.

### What it is

Every conversation turn Sakhi has with a person gets attached to a **topic thread** — a persistent arc that tracks the same subject over days, weeks, months. The system compiles journal entries and conversation turns into a structured arc: origin, key pivots, recurring tensions, current stage, open questions.

This is what makes Sakhi different from a chatbot with memory: it holds the shape of a problem, not just the history.

### What it produces

**In normal conversation** — the current topic's arc is injected silently into every turn. Sakhi knows where you are in this topic's journey without you having to re-explain it. The turn response also returns a signal: `continuity.topic_key`, `continuity.topic_label`, `continuity.deep_reflect` — this is what lets the client unlock deeper surfaces.

**Deep Reflect (chat feature)** — the user types a question, taps Deep Reflect, and gets a synthesis that answers that question using the full arc of the active topic. Async, 5–30s. It pulls from episodic memory (daily summaries from conversations that were never journalled), the temporal spread of journal evidence (early / middle / late moments), cross-thread correlation when a linked topic is available, and a delta since the last reflection run.

The button only appears when the arc has earned it: ≥8 evidence moments, governance permits mirroring, the topic has enough detail surface depth.

**Topic Story (Soul screen, mobile)** — no query. A trace of a single topic arc: what changed, what keeps returning, what remains unresolved, what this reveals. Requires ≥3 moments. Async.

**My Story (Soul screen, mobile)** — no query. Cross-topic synthesis: explicitly connects ≥2 active threads, names one recurring tradeoff, clarifies what matters most right now. Requires ≥6 moments per eligible topic, ≥2 eligible topics. Async.

### The arc compiler

Every time a topic is accessed, the compiler:

1. Pulls journal entries assigned to that thread
2. Resolves ambiguous follow-up entries via a second-pass resolver (so continuation entries don't require keyword repetition)
3. Scores semantic similarity against thread embedding when vectors are present, falls back to lexical match
4. Builds a structured arc object: `arc_compact_global` (origin, pivots, tensions, current stage, open questions)
5. Selects evidence anchors — temporally spread, not just keyword-ranked
6. Caches cross-topic correlations in `continuity_topic_correlations` and life-dimension signals (time, financial, emotional bandwidth) in `continuity_life_dimensions`

The cache has lazy read-through recompute and TTL policy based on profile depth.

### Governance (kala)

kala is a pure-computation kernel. No LLM, no database, no I/O. 552 tests.

What it governs for the continuity engine:

- **mirror_allowed** — can this topic be reflected back to the user at all? kala evaluates constraints against the topic's evidence state
- **detail_allowed** — has sufficient depth been established to surface detailed synthesis?
- **Drift gating** — if the person's current state has drifted significantly from their baseline, kala can block proactive suggestions
- **Contradiction detection** — five categories: previously rejected, contradicts a commitment, repetition loop, outdated objective version, violates a recent override. A suggestion that hits any of these is suppressed
- **State reducer** — events are replayed into deterministic state. Same events → same snapshot, always auditable

The key property: Sakhi earns the right to surface something. kala enforces that earning.

---

## What the MVP Does Not Include (parked)

- Voice pipeline (built, not in live flow)
- HealthKit integration
- Evening closure / morning momentum rituals
- Email intelligence
- Calendar integration
- Soul values, shadow work, alignment screens (built, not in MVP runtime)
- Desktop agent / browser automation
- Mesh (inter-Sakhi coordination)

---

## The Thread

Normal chat → arc builds quietly in the background → Deep Reflect unlocks when the arc has depth → Topic Story traces the full arc → My Story connects the threads.

That's the continuity engine. Each surface is a deeper cut into the same longitudinal model of the person. The user experiences a conversation that remembers. The engine experiences a structured journey with evidence, governance, and earned synthesis.
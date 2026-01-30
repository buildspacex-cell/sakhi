Meta-Reflection Layer (Longer-Horizon Insight)
Purpose of this layer

Detect moments where the user is seeking meaning, clarity, or self-understanding, and seed deeper reflection work that unfolds over time.

This layer exists to support longer-horizon insight, not immediate advice or action.

Step 1: Meta-reflection trigger detection

After intents are extracted, a meta-reflection trigger runs.

It scans intent titles and raw text for introspective signals, such as:

why, meaning, purpose

clarity, values, identity

lost, confused

self, introspect, reflection

If no such signals are present:

Nothing happens

No writes occur

This keeps deep reflection intentional, not ubiquitous.

Step 2: Seeding meta-reflection (backend-only)

If introspective signals are detected, apply_meta_reflection_triggers runs.

It performs three backend actions:

1. Continuity flag

Sets:

session_continuity.reflection_pending = TRUE


Signals that a reflective follow-up is warranted

Does not interrupt the current experience

2. Meta-reflection scoring (aggregate, persistent)

Upserts into meta_reflection_scores

Increments:

helpfulness (+0.05)

clarity (+0.05)

These scores represent accumulated readiness for deeper reflection, not conclusions.

3. Insight work queue

Pushes an item into insights_queue:

{
  source_entry: entry_id,
  kind: "meta_reflection"
}


Priority: medium

No user-facing text is generated at this stage.

Step 3: Reflection generation & delivery (asynchronous)

Separate workers consume this queued work:

A scheduler polls insights_queue

Undelivered items are routed to insight workers

If an insight payload does not yet exist:

reflect_person_memory_delta is invoked to generate reflective content

Generated insights are delivered through the presence / reflection channel

Queue items are marked delivered

In parallel:

Nightly learning jobs may enqueue deeper synthesis

e.g., synthesize_meta_reflection

This allows reflection to mature, rather than react instantly.

What this layer does not do

It does not generate instant answers

It does not infer identity

It does not assign meaning to a single entry

It does not surface introspection unless context supports it

Reflection is earned through pattern, not forced by language.

How this differs from rhythm

Rhythm tracks energy and capacity over time

Meta-reflection tracks meaning and self-inquiry over time

Both:

seed backend intelligence

act slowly

avoid real-time interruption

Design stance (core idea)

Sakhi treats moments of self-questioning as signals for deeper listening — not problems to solve immediately.

Meta-reflection is:

cumulative

asynchronous

context-aware

long-horizon by design

Answering your direct question

Yes — this layer exists to generate longer-term reflection.

Not as a single response, but as:

synthesized insight

periodic reflective prompts

deeper mirrors that draw from accumulated memory

Why this matters

Prevents shallow “why do I feel this way?” responses

Enables meaningful insight without overstepping

Aligns with the product’s philosophy of clarity over coaching


Meta-Reflection Delivery Pipeline

(Deferred Meaning-Making & Presence Delivery)

Purpose (Why this exists)

Meta-reflection is intentionally not generated or delivered inline with a journal or conversation turn.

This pipeline exists to:

acknowledge when deeper reflection is warranted

queue that work safely

synthesize insight with distance and context

deliver it later without interrupting the user

Meta-reflection is treated as slow meaning-making, not immediate feedback.

What gets queued (Trigger phase)

When meta-reflection intents are detected during a turn:

apply_meta_reflection_triggers runs

It performs three actions:

Flags continuity

Sets:

session_continuity.reflection_pending = TRUE


Signals that a deeper reflection should happen later

Accumulates signal

Increments:

meta_reflection_scores


Tracks helpfulness / clarity deltas over time

Queues delivery

Inserts a row into:

insights_queue


With payload:

{
  "person_id": "...",
  "insight": {
    "source_entry": "<entry_id>",
    "kind": "meta_reflection"
  },
  "priority": "medium"
}


No reflection text is generated at this stage.

How it is processed (Synthesis & delivery)
Scheduler-driven processing

A scheduler periodically polls insights_queue for items that:

are not yet delivered

are past deliver_after (if set)

For each eligible item:

Insight synthesis (if needed)

If the queued item does not yet contain an insight payload:

Calls:

reflect_person_memory_delta(person_id, entry_text)


This synthesizes a meta-reflection using:

accumulated memory

identity / soul state

recent patterns and evidence

Delivery

Enqueues the generated insight into:

deliver_insight_to_presence_queue


Marks:

insights_queue.delivered_at


This ensures synthesis and delivery are fully decoupled from the original turn.

Nightly synthesis (broader horizon)

In addition to trigger-based delivery:

A nightly learning job enqueues:

synthesize_meta_reflection


This job:

looks across longer time windows

is not tied to a specific journal entry

generates higher-level, integrative reflections

These are meant to surface patterns of meaning, not responses to moments.

Data written and maintained

insights_queue

Holds pending meta-reflection items until delivery

meta_reflection_scores

Accumulates helpfulness / clarity signals over time

session_continuity

Tracks whether reflection is pending

Presence queue

Receives finalized insights for user-facing surfacing

What this pipeline does not do

Does not block the turn response

Does not generate reflection immediately

Does not create plans or actions

Does not assert conclusions as facts

The pipeline prioritizes timing and readiness over immediacy.
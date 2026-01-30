Memory Spine (Durable Intelligence Layer)
Purpose of the Memory Spine

The Memory Spine is the durable intelligence layer of the system.
Its role is to ensure that what matters over time is remembered, retrievable, and usable — without slowing down live interaction.

It separates:

thinking (fast, conversational, ephemeral)

from remembering (slow, durable, authoritative)

Core design principle

The user should get an immediate, human response —
while memory, recall, and consolidation happen asynchronously and safely in the background.

This decoupling is foundational.

Why a separate Memory Spine exists

If memory were written inline with every turn:

latency would increase

failures would block user interaction

every inference would risk becoming permanent

the system would over-optimize for immediacy instead of truth

Instead, Sakhi uses a worker-driven memory spine that operates independently of the live reply.

How the Memory Spine is activated

During a turn, turn_v2 enqueues a background job:

turn_memory_update


This job is processed asynchronously by workers and is responsible for all heavy memory writes.

The live response is already returned before this work completes.

What the Memory Spine does (authoritative path)

When the worker runs ingest_journal_entry, it performs four categories of work:

1. Embedding & canonical evidence indexing

The journal text is embedded

Embeddings are stored in deep recall structures, not inline session state

These vectors become the basis for:

semantic retrieval

context stitching

longitudinal analysis

This ensures future recall never depends on raw journal scanning alone.

2. Short-term memory (table-based, expiring)

The worker writes a short-term memory slice into a dedicated table:

memory_short_term

Stores:

entry_id

source type

raw text

mood / user tags (if present)

expiration timestamp

Key properties:

bounded

time-limited

evidence-based (no inference stored)

Short-term memory supports near-term continuity, then naturally expires.

3. Deep recall artifacts (compact, retrievable memory)

For each entry, the worker writes deep recall records, including:

context_recalls

compact textual snapshot

sentiment / entities / facets

embedding vector

life_event_links

thread_continuity_markers

context_compact_summaries

These artifacts are:

smaller than raw journals

richer than short-term memory

optimized for retrieval and stitching

Think of them as indexed memory cards, not narrative truth.

4. Long-term consolidation

After short-term and deep recall writes, the worker triggers long-term consolidation.

Conceptually, consolidation answers:

“What should still matter after short-term memory fades?”

This process:

aggregates evidence across time

promotes recurring or salient patterns

ensures older experiences remain accessible to reflection and recall

prevents intelligence decay as entries age

Consolidation is evidence-driven, not speculative.

What the Memory Spine explicitly does not do

It does not generate user-facing text directly

It does not infer identity or intent

It does not overwrite raw evidence

It does not act in real time

It does not commit plans or actions

The Memory Spine is memory, not behavior.

How other systems use the Memory Spine

The outputs of the Memory Spine feed into:

context builders for future conversations

weekly and meta-reflection synthesis

rhythm forecasting

longitudinal pattern awareness

explainability and auditability

All higher-level intelligence depends on this spine — none bypass it.

Architectural stance (this is the key message)

Sakhi remembers slowly and deliberately.

Live interaction stays human and responsive

Memory is written once, carefully, and off the critical path

Intelligence grows from accumulated evidence, not single moments

This design prevents:

premature conclusions

runaway inference

brittle personalization

Why this matters (externally)

This architecture enables Sakhi to:

scale without latency collapse

remain trustworthy over long time horizons

evolve intelligence without corrupting history

support deep reflection without surveillance-like behavior

Most systems conflate chat memory with personal memory.
Sakhi treats memory as a first-class system.

One-line summary (useful closer)

Live turns think.
The Memory Spine remembers.

The artifacts written by the Memory Spine are not passive storage; each has a specific downstream role:

memory_short_term

Feeds near-term recall and consolidation

Provides recent evidence context before expiration

Acts as the bridge between live turns and longer-horizon memory

context_recalls

Primary input to semantic recall and context builders

Supplies compact, vectorized memory slices for future turns and reflections

life_event_links

Enable association of entries with longer-lived life themes or events

Support longitudinal pattern recognition and narrative stitching

context_compact_summaries

Provide compressed, human-readable snapshots

Used when constructing higher-level reflections without reprocessing raw journals

thread_continuity_markers

Preserve conversational and experiential continuity across time

Allow future interactions to resume threads without relying on session state

Reinforcing design intent

Each memory artifact has a clear consumer.
Nothing is written “just in case.”

This ensures:

memory remains purposeful

recall stays explainable

intelligence layers build only on justified evidence
Memory Event Fan-Out

(Asynchronous Memory Maintenance Hub)

What this is

Memory event fan-out is the background handler for the memory.entry.observed event.

It acts as a single coordination point that reacts to a new memory being observed and dispatches multiple maintenance updates without blocking the live turn.

When it runs

turn_v2 publishes a MEMORY_EVENT with:

person_id

entry_id

text

layer

A scheduler subscribes to this topic

The handler memory_event_fanout runs asynchronously

This happens after the response is already returned.

What the fan-out does

For each observed memory event, it fans out the following background work:

Relationship updates

Updates relationship arcs based on the text

Keeps trust / attunement / relationship continuity current

Memory consolidation

Triggers consolidation logic

Ensures the entry participates in long-term memory structures

Recall graph reinforcement

If person_id + entry_id are present:

Reinforces or adjusts recall graph connections

Keeps memory linkage strength up to date

Journal re-ingest (journal layer only)

If layer == "journal":

Re-ingests the journal entry

Ensures downstream memory pipelines stay consistent

What it explicitly does not do

Does not affect the live reply

Does not generate insights

Does not block turn_v2

Does not introduce new intelligence

It is maintenance orchestration, not reasoning.

Why this exists (design rationale)

Without memory event fan-out, every subsystem would need to:

listen to turns independently

duplicate triggering logic

risk inconsistent updates

Instead:

One observed memory → many quiet updates.

This keeps the system:

modular

decoupled

easy to extend

safe under latency constraints

How it fits the overall storyline
Journal / Turn
     ↓
memory.entry.observed
     ↓
Memory Event Fan-Out
     ↓
Relationship updates
Memory consolidation
Recall graph reinforcement
Journal re-ingest (if applicable)


This explains how multiple background systems stay in sync without inflating the turn path.

Where this sits in the master structure

Conceptually, this belongs as a subsection under the Memory Spine / Async Infrastructure, not as a new layer.

It answers:

“How do all these background memory updates stay coordinated?”

One-line anchor (keep this)

Memory event fan-out lets one experience quietly update many internal systems.
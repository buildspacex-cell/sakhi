Build: Episodic Memory Audit

(Meaningful Events / Consolidation Layer)

Build ID: EP-AUDIT-01
Status: Audit Complete
Scope: Episodic Memory (memory_episodic)
Date: (fill)
Owner: Sakhi Core

1. Purpose of This Build

This build audits Episodic Memory to determine whether it fulfills its intended role as:

A durable, stable record of significant moments (“what happened”),
derived intentionally from recent evidence,
and suitable for reflection and narrative continuity.

The goal is not to refactor yet, but to:

lock the intended contract,

inspect current behavior,

identify drift,

and decide whether episodic memory can support human-level reflection as-is.

2. Intended Contract (Authoritative)
Definition

Episodic memory is the durable “what happened” layer.
It stores consolidated, meaningful episodes derived from recent journals and turns, intended to be stable once recorded.
It captures lived moments worth recalling, with enough structure for reflection and continuity — without collapsing into identity or long-term belief.

What Episodic Memory SHOULD Store

A. Episode identity & scope

episode_id

person_id

source entry IDs (journals / turns)

time scope or window

B. Consolidated episodic meaning

concise episode summary (interpreted, not verbatim)

expressed mood / affect

contextual themes

C. Recall & retrieval signals

embeddings

salience / importance

episode-level tags

cadence / time features

D. Provenance & stability

created_at

content hash

worker / model version

confidence or quality marker (optional)

What Episodic Memory MUST NEVER Store

Raw journal text (primary evidence lives in journals)

STM-style payloads or caches

Identity traits or beliefs

Long-term persona hypotheses

Mutable scratch data

Weekly synthesis or conclusions

3. How Episodic Memory Differs from Other Layers
Layer	Role
Journals	Immutable raw evidence (verbatim text + capture metadata)
STM	Disposable, short-lived working window of recent evidence
Episodic	Durable, curated “what happened” records
Personal / Long-Term Model	Aggregated patterns and hypotheses across episodes

Episodic memory sits between STM and long-term modeling.

4. Current Schema Snapshot (Observed)

memory_episodic currently contains a mixture of:

Legitimate episode fields

id

user_id / person_id

entry_id

time_scope

created_at, updated_at

content_hash

Episodic meaning & recall

text (normalized / summary)

vector_vec

context_tags

emotion_loop

Identity / long-term signals (drift)

soul

soul_shadow

soul_light

soul_conflict

soul_friction

soul_vector

Legacy / STM-like payloads (drift)

record jsonb (text, sentiment, entities, facets, tags, embeddings)

5. Write-Path Reality (Current Behavior)
Episode creation

Episodes are created immediately on journal/turn ingest.

STM and episodic are written in the same ingest flow (dual-write).

There is no promotion step.

Deduplication

Path-dependent and inconsistent:

(user_id, content_hash) in heavy ingest

entry_id conflict in experience_journal

none in worker ingest

Mutation after insert

context_tags appended post-insert (wellness, emotion_loop, arc_stage)

soul* fields written later by LLM workers

No append-only guarantees

No versioning (only updated_at)

Deletion / merging

None observed

No TTL or lifecycle management

6. Single Episode Walkthrough (Current)

Journal/turn ingested

STM written immediately

Episodic row inserted in same flow

Context tags updated (wellness/emotion_loop/arc_stage)

Soul worker later overwrites soul fields

Episode meaning can change days later

Key fact:

An episode is not promoted, finalized, or stabilized — it is auto-created and perpetually mutable.

7. Contract Comparison — Episodic vs Target
Matches

Episodes derive from recent evidence

Identity keys and timestamps are present

Embeddings support recall

Context tags attempt to capture salient signals

Violations

Episodes are created automatically (no salience or selection)

Single turns become episodes (no consolidation)

Derived signals injected immediately

Identity-level soul fields live in episodic rows

Worker paths mix STM-like payloads into episodic

Episodes mutate over time (no stability, no versioning)

Ambiguous / drifting areas

Dedup rules differ by ingest path

Episode definition varies by insert path

Arc/narrative tags computed ad hoc on ingest, not after significance assessment

8. Final Assessment

Episodic memory currently acts as an auto-written, mutable enrichment table — not a curated, stable record of significant events.

Because:

there is no promotion step,

no stability guarantee,

and no boundary between episodic meaning and long-term identity,

episodic memory cannot yet serve as the backbone for reflection or narrative continuity.

9. Why This Matters

If episodic memory remains as-is:

Reflection reasons over unstable meaning

Narrative continuity becomes untrustworthy

Identity hypotheses overwrite lived history

Weekly mirrors feel inconsistent or “off”

This is the same structural problem already corrected in:

Step 1 — Journals

Step 2 — STM

It now needs to be corrected here.

10. Non-Goals of This Build

This audit does not:

Refactor episodic memory

Remove soul data

Define promotion criteria

Redesign reflection logic

Those belong to the next build.

11. Follow-On Build Enabled

This audit directly enables:

EP-REFORM-01 — Episodic Memory Reform

Where we will:

separate promotion from ingestion,

freeze episodes once created,

remove identity/soul from episodic,

and restore episodic memory to a trustworthy “what happened” layer.

12. Summary (One Paragraph)

This build audits Episodic Memory and finds significant drift from its intended role. Episodes are created automatically alongside ingestion, mutated over time, and overloaded with inference and identity-level signals. As a result, episodic memory functions as a mutable enrichment sink rather than a stable record of significant events. This audit locks the diagnosis and sets the stage for a principled reform that will restore episodic memory as a durable, trustworthy foundation for reflection and narrative continuity.
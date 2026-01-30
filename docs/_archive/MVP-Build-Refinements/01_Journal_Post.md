Build: Raw Evidence Hardening & Inference Boundary

Build ID: RE-01
Status: Complete
Scope: Journal Evidence Layer
Date: (fill in)
Owner: Sakhi Core

1. Purpose of This Build

This build establishes a canonical, immutable Raw Evidence Layer for Sakhi.

It guarantees that:

What a user writes is never mutated

Evidence is separated from interpretation

Future reflection and intelligence layers can re-run, revise, and improve meaning without corrupting history

This is a foundational architectural decision for building trustworthy, human-level reflection.

2. Functional Outcomes (What This Build Achieves)
✅ Evidence Integrity

Raw journal content is immutable after insert

No worker, model, or future code path can alter what the user originally wrote

✅ Clean Layer Separation

Journals store what the human said

Interpretation and enrichment are explicitly downstream concerns

✅ Reflection-Safe Architecture

Weekly / long-term reflection can rely on evidence as:

stable

replayable

auditable

✅ Future-Proofing

Meaning can evolve

Models can be replaced

Inference can be re-run

Evidence remains unchanged

3. Conceptual Model
Layering Principle
Raw Evidence (Immutable)
        ↓
Entry-Level Inference (Replaceable)
        ↓
Short-Term Memory
        ↓
Weekly / Long-Term Reflection


This build locks the bottom layer.

4. Tables Involved
4.1 journal_entries — Raw Evidence Layer

Role:
Stores raw, user-authored journal entries and capture-time metadata only.

Contract:

Append-only for raw content

No derived or inferred meaning allowed

Immutable at the database level

Key Columns
Column	Type	Description
id	uuid	Primary key
user_id	uuid	Owner of the entry
content	text	Raw user-authored text (immutable)
title	text	Optional user-provided title
layer	text	Capture layer (journal / experience / memory)
mood	text	Explicit user-provided mood (optional)
user_tags	text[]	Explicit user-provided tags only
source_ref	text / jsonb	Capture instrumentation (where this came from)
created_at	timestamptz	Time of capture
updated_at	timestamptz	Metadata updates only
Explicitly Forbidden in This Table

Sentiment scores

Emotional classification

Intent inference

Domains / facets

Narrative summaries

Salience / priority scores

System-generated tags

4.2 Evidence Immutability Enforcement

Mechanism:
PostgreSQL trigger: trg_journal_content_immutable

Behavior:

Fires BEFORE UPDATE on journal_entries

Rejects any update where OLD.content ≠ NEW.content

Allows updates to all other columns

Rationale:
Application-level conventions are insufficient for evidence integrity.

4.3 journal_inference (Target Downstream Layer)

Note: Defined in a subsequent build; referenced here for clarity.

Role:
Stores atomic, entry-level system interpretations derived from a single journal entry.

This build does not populate it yet, but establishes the boundary that all interpretation must live here.

5. Inference Philosophy (Important Context)

Sakhi reasons about human experience using five base containers:

Affect — emotional state

Cognition — mental / thinking state

Somatic — perceived bodily state

Vitality — energy / capacity state

Context — life domain (work, family, health, self)

These are lenses, not fixed taxonomies.

This build ensures that none of these interpretations contaminate raw evidence.

6. What Is Stored vs What Is Deferred
Stored Now (in journal_entries)

Raw text

Explicit user inputs

Capture metadata

Deferred to Downstream Layers

Sentiment / emotion classification

Intent / domain detection

Body or energy inference

Salience or importance

Narrative summaries

Reflection or pattern detection

This deferral is intentional.

7. Why This Matters (Design Rationale)

Most AI systems:

Mix evidence and interpretation

Rewrite history as models improve

Lose trust over time

Sakhi deliberately avoids this.

Evidence is sacred. Meaning is provisional.

This allows Sakhi to:

Reflect instead of dictate

Evolve without gaslighting

Remain humane and trustworthy

8. Non-Goals of This Build

This build does not:

Modify enrichment workers

Introduce reflection logic

Define memory aggregation

Backfill historical inference

Optimize retrieval

Those belong to later builds.

9. Follow-On Builds

This build enables:

RE-02: Entry-Level Inference Population

STM-01: Short-Term Memory Formation

WR-01: Weekly Reflection Engine

LM-01: Long-Term Narrative & Rhythm Modeling

Each can now proceed safely.

10. Summary (One Paragraph)

This build establishes an immutable Raw Evidence Layer for Sakhi by enforcing database-level protection on journal content and clearly separating evidence from interpretation. It ensures that what a human writes is never altered, while allowing system intelligence to evolve downstream. This architectural decision is foundational for building trustworthy, human-level reflection and long-term personal intelligence.
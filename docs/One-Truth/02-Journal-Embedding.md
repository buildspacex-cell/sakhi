Journal Embeddings (Retrieval Layer)

Purpose

Maintain one semantic embedding per journal entry so future recall and retrieval can operate via similarity search.

This layer exists purely for retrieval, not interpretation.

Where it lives

Table: journal_embeddings

Defined in migration: 0001_init.sql

Structure

One row per journal entry

Primary key: entry_id (UUID)

Foreign key: entry_id → journal_entries.id

ON DELETE CASCADE (embeddings never outlive their source evidence)

Data stored

embedding — vector(1536) (required)

created_at — timestamp, default now()

Indexing

IVFFlat index on embedding

Distance metric: cosine

Optimized for fast similarity lookups during recall

Explicit constraints

No additional fields

No tags, labels, summaries, sentiment, or metadata

This table contains only vectors + time

How it is populated (Runtime Behavior)

Trigger

After a journal entry is written, a follow-up task is launched:

generate_journal_embedding(entry_id, text)

Execution model

Runs as a background async task (asyncio.create_task)

The API response does not wait for embedding generation

User-facing latency is unaffected

What the task does

Computes a single 1536-dimensional embedding from the journal text

Writes one row into journal_embeddings for that entry_id

Sets the timestamp

What it does not do

Does not modify journal_entries

Does not infer meaning, identity, mood, or intent

Does not write anywhere else

Why this matters (Design Intent)

Evidence (journal_entries) and retrieval (journal_embeddings) are cleanly separated

Embeddings are derivative and disposable

Deleting a journal entry deterministically removes its embedding

Intelligence can evolve without ever corrupting or rewriting raw user truth

This section is very strong technically — it shows:

Deterministic data flow

Clear async boundaries

No hidden coupling between “intelligence” and “evidence”
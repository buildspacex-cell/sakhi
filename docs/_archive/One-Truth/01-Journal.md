1. Journal Ingestion (Source of Truth)

What the user does

The user writes and submits a journal entry.

What the system does first

A new row is written to journal_entries.

Data stored

Required

user_id

content — full journal text

Defaults

layer = "journal"

created_at / updated_at = now

Critical design choice

The journal text is stored verbatim.

No trimming, summarization, rewriting, or interpretation is applied at ingest time.

Why this matters

journal_entries.content is the single source of truth for the user’s lived interaction.

Every downstream signal, reflection, or intelligence is derived from this raw evidence — never replacing it.

This is a strong foundation section: it establishes trust, determinism, and philosophical intent (evidence before intelligence).
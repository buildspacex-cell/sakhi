Short-Term Memory (Immediate Context Window)

Purpose

Maintain a small, recent context window of a user’s latest journal entries.

This memory supports continuity and near-term reflection, not identity formation or advice.

What is computed (inline)

Immediately after the journal embedding is available:

Topics are extracted
(extract_topics_for_entry)

Emotion is detected
(detect_emotion_for_entry)

These signals are computed synchronously and used immediately.

What is written (strictly bounded)

Short-term memory is enriched using:

the raw journal text

extracted topics

detected emotion

the journal embedding

Each short-term memory item contains only:

entry_id

text (verbatim journal content)

topics[]

emotion{}

embedding[]

Deliberately excluded

Goals, plans, or intents

Triggers or behavioral labels

Narrative arcs or interpretations

Identity traits or long-term attributes

This boundary is intentional and enforced.

Where it is stored

Storage location: personal_model.short_term

Format: JSON array on the user’s personal_model record

Write behavior

A new item is appended to the short-term list

The list is capped to the most recent ~20 entries

Older items naturally fall off

personal_model.updated_at is refreshed

There is no separate short-term memory table.

Design intent (why this matters)

Short-term memory is contextual, not authoritative

It is bounded, overwrite-prone, and non-durable by design

Signals here can support reflection, but cannot silently become long-term truth

Intelligence can look at short-term memory,
but short-term memory does not define the person.

Architectural choice (locked)

Short-term memory remains embedded inside personal_model as a JSON structure.

This reinforces:

ephemerality over permanence

context over data accumulation

safety over over-interpretation
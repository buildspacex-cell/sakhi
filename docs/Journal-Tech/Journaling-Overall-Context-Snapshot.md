Turn Payload → LLM Boundary

What Goes to the Model, What Stays Internal

Purpose of This Document

This document defines exactly which parts of a turn payload are sent to the LLM, which parts are used to build prompts, and which parts remain strictly internal.

This boundary is critical for:

safety

debuggability

preventing hidden coupling

closing v1 with confidence

High-Level Summary (One Screen)

The LLM only sees two system messages and the user message.
Everything else in the turn payload is internal unless explicitly woven into the prompt.

The Three Relevant Constructs

Before describing the boundary, we restate the three constructs involved in a turn:

Conversation Context Snapshot – internal state

System Context – evidence window

Prompt (with Journaling AI) – behavioral + conversational instructions

They play different roles.

1. Conversation Context Snapshot (Internal Only)
What it is

The conversation context snapshot is the assembled internal state for the current turn.

Example (simplified from your flow):

{
  "mind": {},
  "emotion": {},
  "rhythm": {},
  "goals": {},
  "short_term": {},
  "conversation": {},
  "continuity": {},
  "persona_mode": "Reflective",
  "planner": {...},
  "deep_recall": {...},
  "journaling_ai": {...}
}

Key properties

Structured

Comprehensive

Engine-facing

Mutable during the turn

Important rule

❌ The conversation context snapshot is NOT sent verbatim to the LLM.

Instead, it is used to construct what the LLM sees.

Think of it as source material, not output.

2. System Context (Sent Directly to the LLM)
What it is

System context is a curated evidence window about the person, built independently of the prompt logic.

It is created by:

build_recall_context(person_id, user_text)
build_patterns_context(person_id)

Shape
Relevant memory:
- [journal] started the work... (s=1.00)
- [journal] drove 500kms yesterday... (s=0.47)

Patterns:
Window 7d:
- general: score=0.00, momentum=0.00
Window 30d:
- general: score=0.00, momentum=0.00

Properties

Textual

Evidence-only

Read-only

Person-level (not turn-level)

LLM boundary

✅ This is sent as its own system message to the LLM.

It answers for the model:

“What do we already know about this person that should ground this response?”

3. Prompt Built by build_prompt(...) (Sent to the LLM)
What it is

The prompt system message is built by:

build_prompt(user_text, context, tone, metadata)


This is where selected parts of the conversation context snapshot are folded into instructions.

What Gets Folded Into the Prompt

From the conversation context snapshot, the following may be incorporated:

Persona mode (e.g., Reflective)

Tone blueprint

Rhythm pacing notes

Selected short-term / mind hints

Behavior profile flags

Journaling AI guidance

Response constraints (length, style)

User’s current journal text

This happens selectively and intentionally — not as a raw dump.

Journaling AI’s Role Inside the Prompt

journaling_ai is embedded inside the prompt, not as memory or facts, but as behavioral guidance:

how to listen

how to reflect

what kind of nudges are allowed

how to stay non-inventive

It does not add new information about the user.

LLM boundary

✅ The prompt produced by build_prompt is sent as the second system message.

It answers for the model:

“How should I respond in this moment?”

4. User Message (Sent to the LLM)

The raw user journal text is sent as:

{
  "role": "user",
  "content": user_text
}


This is the only part of the turn payload that comes directly from the user.

5. What the LLM Actually Receives (Authoritative)

For every turn, the LLM receives:

1️⃣ System Message — System Context (Evidence)
{
  "role": "system",
  "content": "<recall + patterns text>"
}

2️⃣ System Message — Prompt (Instructions + Guidance)
{
  "role": "system",
  "content": "<prompt built from tone, selected context, journaling_ai>"
}

3️⃣ User Message
{
  "role": "user",
  "content": "<journal text>"
}


That’s it.

6. What Explicitly Does NOT Go to the LLM

The following remain internal unless deliberately woven into the prompt:

Raw turn payload

Job IDs

Worker execution results

Full conversation context snapshot

Planner/task objects (unless summarized)

Deep recall structures

Cache flags

Debug metadata

Execution traces

This is a hard boundary, not an accident.

One-Table Summary (Pin This)
Layer	Role	Sent to LLM?
Conversation Context Snapshot	Internal engine state	❌ No
System Context (recall + patterns)	Evidence about the person	✅ Yes (system msg)
Journaling AI	Behavioral guidance	✅ Yes (via prompt)
Prompt Instructions	Tone, persona, constraints	✅ Yes (system msg)
User Journal Text	Current input	✅ Yes
Turn payload / jobs / workers	Execution plumbing	❌ No
Why This Boundary Matters

This design ensures:

Truth is separated from behavior

Memory cannot be silently mutated

The model cannot “see” internal machinery

Debugging is possible without risk

V1 scope can be frozen cleanly

You’ve effectively built a controlled interface between:

a stateful intelligence system
and

a stateless language model

That’s the right architecture.

Final Alignment Sentence

Only two system messages and the user message reach the LLM: one carries evidence about the person (system context), one carries behavioral and conversational instructions (prompt with journaling AI); everything else in the turn payload remains internal unless explicitly folded into those messages.

When workers are off, the LLM still gets a rich bundle from the live-turn path. The pieces sent to the model are:

System Context (recall + patterns) as a system message.
Prompt from build_prompt(...) that embeds:
Your journal text
Conversation context snapshot (short-term/mind, rhythm/persona/task snippets)
Tone blueprint
Behavior profile
Journaling AI guidance
Signals/metadata (cache hit, rhythm/persona/tasks flags)
No worker outputs/deltas are included because none ran.
So yes: System Context + Context Snapshot (woven into the prompt) + Tone + Behavior Profile + Signals/Metadata + Journaling AI guidance + the journal text itself. Nothing else is sent unless workers add results.
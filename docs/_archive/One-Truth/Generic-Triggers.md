Generic Trigger Hints (Non-Executing Classification Layer)

Status: Implemented, not consumed
Audience: Internal (engineering / architecture reference)
Included in presentation: ❌ No

Purpose of this layer

The Generic Trigger step provides a lightweight classification of a turn, answering:

“What kind of interaction was this?”

It does not execute actions, enqueue jobs, write to storage, or affect user-facing behavior.

This layer exists as routing and observability scaffolding, not as an active intelligence or workflow driver.

When it runs

Executed during the turn_v2 flow

Runs after:

journal ingestion

intent extraction

mood normalization

Receives:

extracted intents

journal content

normalized mood

What it computes

compute_triggers produces a flag dictionary of boolean hints:

{
  rhythm,
  meta_reflection,
  planner_summarizer,
  persona_tuning,
  memory_consolidation
}


Each flag indicates that the turn may be relevant to a downstream system.

How flags are determined (examples)

rhythm

intent mentions energy, rhythm, review_week

mood is tired, anxious, overwhelmed, stuck

meta_reflection

intent like reflect_deep

journal mentions weekly reflection, learning, meaning

planner_summarizer

intent mentions plan, task, objective

persona_tuning

identity or self-expression language

memory_consolidation

reflective language

emotionally salient moods (sad, happy, excited)

daily/summary-style entries

These rules are heuristic, not learned.

What this layer explicitly does not do

❌ Does not enqueue background jobs

❌ Does not write to any database table

❌ Does not modify the turn response

❌ Does not influence planner, rhythm, or reflection execution

❌ Does not persist any signals

The flags are returned only as metadata in the turn response bundle.

Runtime behavior (current state)

Flags are computed

Flags are attached to the response payload

No worker or scheduler in the codebase consumes them

No follow-on processing occurs as a result

In practical terms, they are inert hints.

Architectural intent (original design)

This layer was designed as a future routing switch, enabling a flow like:

turn → compute_triggers
         ↓
scheduler decides:
  - run rhythm forecast
  - enqueue reflection
  - summarize planner state
  - tune persona


In practice, this role has been superseded by:

explicit rhythm triggers

explicit meta-reflection triggers

explicit planner commit paths

Those systems are more precise and safer.

Why this layer still exists

Classification lens

Encodes “what kind of turn was this?” in a normalized way

Future extensibility

Could later feed a policy engine or learned scheduler

Debugging / observability

Useful for internal inspection of turn intent without side effects

Why it is excluded from the presentation

It does not affect system behavior

It introduces unnecessary complexity

It suggests unfinished automation where none exists

The real system uses explicit, auditable triggers instead

Including it externally would reduce clarity.

Recommendation (locked)

Keep compute_triggers as internal scaffolding

Do not rely on it for execution

Do not surface it to users or investors

Revisit only if/when a unified scheduling or policy layer is introduced

One-line internal summary

Generic triggers classify turns but do not act on them; they exist as future-facing routing hints and internal observability only.
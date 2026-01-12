Conversation & Response Assembly

(How Sakhi Responds in a Live Turn)

Purpose of this layer

This layer explains how Sakhi assembles context and generates a response for a single turn.

The goal is:

to speak with the latest available understanding of the user

without waiting for slower background workers

without recomputing heavy intelligence inline

The reply is grounded in state that already exists — not built on the fly.

When this happens

Runs inside turn_v2

Happens before the assistant reply is generated

Completes synchronously, but only using:

cached state

lightweight inference

already-available artifacts

No long-running jobs block the response.

Step 1 — Memory snapshot
What happens

Loads a compact memory/context snapshot via load_memory_context

If not in minimal mode:

synthesizes a fresh, human-readable memory context string using synthesize_memory_context

Why

Provides continuity without pulling full history

Keeps memory bounded and relevant

Memory is summarized, not replayed.

Step 2 — Turn orchestration (signal extraction)
What happens (orchestrate_turn)

Saves the journal entry

Embeds it

Extracts:

topics

emotion

intents

ephemeral plans (full mode)

Detects rhythm and meta-reflection triggers

Why

Captures what just happened

Produces fresh signals without committing state

These signals are used immediately for grounding the reply.

Step 3 — Behavior profile & brain state
What happens (run_unified_turn)

Builds a behavior profile for the turn:

tone

depth

assertiveness

guidance level

Consults the Brain Engine for cached state:

goals / planner context

rhythm state

emotional baseline

identity / soul

relationship state

environment context

habits, focus, priorities

Why

Ensures the reply is aligned with the whole person, not just the last message

The assistant speaks from state, not inference.

Step 4 — Internal state pull (personal model)
What happens

Pulls derived summaries from personal_model, including:

emotional / mental summaries

priority topics

soul values and identity themes

rhythm and identity frames

continuity markers

tone / empathy / micro-regulation state

Why

These summaries are already curated

They avoid re-deriving meaning inline

Step 5 — Cached daily & micro flows
What happens

Reads precomputed experience artifacts from caches:

Morning preview / ask / momentum

Micro-momentum / micro-recovery

Evening closure

Focus path

Mini-flow

Micro-journey

Each is passed through its guard logic to decide relevance.

Why

Keeps responses timely and contextual

Avoids recomputing daily guidance during the turn

Experiences are prepared ahead of time, not improvised.

Step 6 — Optional reasoning & recall
What happens

If not in minimal mode and the behavior profile warrants it:

runs lightweight reasoning

may fetch memory recall results

may update conversation topics or persona inline

Why

Reasoning is conditional, not default

Prevents overthinking or verbosity

Step 7 — Reply generation
What happens

All assembled context is packaged into:

metadata

behavior profile

Sent to generate_reply

Returns:

assistant text

tone blueprint

Why

Generation happens after context assembly

The LLM does not need to guess state

The model writes; the system grounds.

Step 8 — Response payload & background continuation
What happens

The API response returns:

The assistant reply

Contextual metadata:

internal state snapshots

cached flows

topics / persona signals

reasoning / recall (if used)

A list of queued background jobs that will:

update memory

refresh planner, rhythm, persona, insights

continue learning after the reply

Why

The user gets an immediate, grounded response

The system continues evolving afterward

Net effect (important summary)

The response is generated using:

fresh turn signals

cached brain/persona/rhythm/planner state

precomputed daily & micro flows

All gathered before generate_reply.

The assistant never waits for:

consolidation

deep learning

graph building

nightly synthesis

What this layer does not do

Does not block on background workers

Does not recompute identity or rhythm

Does not persist heavy state inline

Does not guess missing context

Core storyline anchor (add this to your spine)

Sakhi responds from what it already knows — and learns more afterward.

One-line summary

Conversation is grounded synchronously; intelligence evolves asynchronously.
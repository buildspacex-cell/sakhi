Memory Graph

(Relational Memory Structure — Latent Infrastructure)

Purpose of this layer

The Memory Graph layer creates a connected representation of the user’s inner world by linking themes, rhythm signals, emotional tones, and reflections into a graph of nodes and edges.

Its purpose is not immediate behavior, but to establish relational structure that can support richer recall, explanation, and reasoning over time.

This layer is intentionally kept outside the turn path.

Why this layer exists

Flat memory (lists, tables, embeddings) can answer:

what happened

what is similar

But it struggles to answer:

what tends to co-occur

what reinforces or conflicts

how patterns relate across domains (energy, emotion, meaning)

The memory graph exists to model relationships, not events.

Sakhi does not just remember experiences — it remembers how experiences connect.

When it runs

Implemented as a background worker task

Never runs inline with a live turn

Does not block reflection, conversation, or planning

This makes the graph:

safe to build probabilistically

safe to revise

safe to ignore if imperfect

What the memory_graph_builder does
Inputs (bounded, recent)

For a given person, the worker gathers a limited sample:

up to 10 reflections

up to 10 journal themes

up to 5 rhythm insights

up to 10 emotional tones

This keeps graph construction:

scoped

repeatable

computationally bounded

How the graph is constructed

The worker prompts an LLM to:

“Build or update a holistic user memory graph.”

The LLM returns structured JSON describing:

Nodes

Each node represents a meaningful concept such as:

a theme

an emotional pattern

a rhythm state

a reflection concept

Each node includes:

node_kind (theme / emotion / rhythm / reflection / etc.)

label

optional data payload

Edges

Each edge represents a relationship between two nodes:

from_node

to_node

relation (e.g., reinforces, conflicts_with, co_occurs_with)

weight (strength)

What gets stored

The parsed output is written to two tables:

memory_nodes

node_kind

label

data (JSON)

memory_edges

from_node

to_node

relation

weight

Edges are interpretive hypotheses, not facts.

How it is used today
Active usage (current state)

The only in-repo consumer is reflective_loop

User feedback on reflections is used to:

adjust memory_edges.relevance

strengthen or weaken connections over time

This allows the graph to be tuned by response, not just inferred.

Intended usage (architectural role)

Even where not yet wired, the graph is designed to support:

Graph-augmented recall

retrieving memories connected by relationship, not just similarity

Explainability

“This insight connects your energy dips with work-pressure themes”

Narrative and soul reasoning

life arcs, conflicts, evolution paths are graph-native structures

Drift and pattern detection

changes in edge strength over time indicate shifting priorities or resolution

The graph is foundational structure, not an execution dependency.

What this layer explicitly does not do

Does not generate user-facing language

Does not override memory spine records

Does not create goals, plans, or actions

Does not influence live turn responses

Does not claim truth — only relationships

The graph proposes connections; the system earns confidence through repetition and feedback.

Why it is intentionally latent

The memory graph is designed to exist before it is relied upon.

This allows:

safe experimentation with relational structure

gradual tuning via feedback

future reasoning upgrades without re-architecting memory

Sakhi builds relational structure before it depends on it.

How it fits the overall storyline
Journals → Memory Spine → Themes / Rhythm / Reflections
                                  ↓
                           Memory Graph (latent)
                                  ↓
                   Future recall, explanation, narrative


The graph augments intelligence; it does not gate it.

One-line anchor (for recall & presentation)

Memory is not just what happened — it’s how things connect.
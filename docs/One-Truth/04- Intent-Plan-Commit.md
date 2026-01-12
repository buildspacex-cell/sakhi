Intents, Planning, and the Commit Boundary
Purpose of this layer

Translate reflection into potential action — without prematurely committing the user to tasks, goals, or schedules.

This layer exists to support decision-making, not to automate behavior.

Step 1: Intent extraction (inference, not memory)

After topics and emotion are computed for a journal entry:

An intent extractor runs on the same entry

Intents represent structured action or goal signals implied by the user’s words

Each intent is enriched with:

id

person_id

entry_id

Key principle

Intents are inferred signals

They are not durable memory

They do not represent user commitment

Step 2: From intent → plan suggestion (still ephemeral)

Extracted intents are passed into a planning step:

plan_from_intents converts each intent into a suggested plan item

A plan suggestion may include:

label (what the action could be)

reference to the intent

optional timing or priority hints

At this stage:

Plans are proposals

They exist only in memory

Nothing is written to planner or action tables

This enables Sakhi to think about action without taking action.

Step 3: Conversational use of plan suggestions

These in-memory plan suggestions may be:

surfaced in the response

used to guide follow-up questions

referenced in conversational planning (“Would you like to act on this?”)

They influence how Sakhi responds, not what Sakhi commits.

Once the turn completes, these suggestions expire unless explicitly promoted.

Step 4: The commit boundary (where persistence begins)

Plans or actions become durable only when they cross an explicit commit boundary.

There are two supported ways this happens:

1. Explicit user confirmation

The user clearly asks to create, track, or schedule something

The system calls /planner/commit

planner_commit upserts into planner tables:

goals

milestones

planned items (tasks / actions)

2. Intentional background promotion

A background worker evaluates a turn

If it deliberately promotes suggestions, it calls the same commit helper

The same planner tables are written

There is no alternate persistence path

All persistent plans flow through one commit mechanism.

What this system explicitly avoids

No automatic task creation from language alone

No silent scheduling

No accumulation of inferred intent as long-term truth

No planner writes without an explicit commit

Design stance (this is the point of the section)

Sakhi separates thinking about action from taking action.
It can suggest, explore, and help plan — but it only commits when the user does.

This protects:

user agency

trust

explainability

long-term system integrity

Why this matters for the product

Reflection stays safe and human

Planning becomes collaborative, not coercive

The system scales without accumulating false commitments

Future planner sophistication can be added without breaking trust



Section 4 — The Two-Planner Contract System
Purpose of this section

Explain how Sakhi supports planning without collapsing reflection into task automation, while still ensuring that explicit commitments are not forgotten.

This section defines two distinct planner contracts that coexist by design.

Core principle

Sakhi separates considering action from recording commitment.

Both are necessary.
They operate at different moments, with different guarantees.

Planner Contract A: Conversational Planning (Non-Committal)
What this contract is for

Support thinking, exploration, and decision-making in conversation — without assuming intent or taking control.

This contract governs the live turn.

How it works

Intents are inferred from the journal or conversation

Intents are transformed into suggested plan items

Suggestions may be referenced conversationally:

to ask clarifying questions

to help the user think through options

All plans remain in memory only

What this contract guarantees

No planner tables are written

No tasks, goals, or schedules are created

No commitments are assumed

Everything expires with the turn unless explicitly promoted

This preserves:

user agency

psychological safety

trust during reflection

Design stance

When Sakhi is thinking with the user, it never commits for the user.

This is the default, visible planning behavior.

Planner Contract B: Background Planner Ingestion (Commit Recording)
What this contract is for

Ensure that explicitly stated commitments expressed in natural language are not lost, even if the user does not manually enter them into a planner UI.

This contract governs background synchronization, not conversation.

How it works

Every turn enqueues a background planner update

The worker analyzes the turn text for explicit task-like structure

If no tasks are found:

nothing is written

If tasks are found:

goals, milestones, and tasks are persisted via a single commit mechanism

planner caches, rhythm alignment, and growth state are updated

All of this happens after the live reply is delivered.

What this contract guarantees

Only turns with clear task structure affect the planner

Reflective or exploratory journals remain inert

Persistence is deterministic and auditable

Planner state stays aligned with what the user has already said they will do

Design stance

Sakhi does not decide what the user should do —
but it remembers what the user has already decided to do.

This contract is invisible to the user unless they later inspect their planner.

Why both contracts are necessary

Without Conversational Planning:

reflection collapses into automation

every thought risks becoming a task

trust erodes

Without Background Planner Ingestion:

users naturally state commitments

Sakhi forgets them

the planner becomes incomplete and unreliable

Together, they allow Sakhi to be:

thoughtful without being passive

helpful without being coercive

accurate without being intrusive

The reconciliation (single mental model)
User exploring → Conversational Planning (suggest, ask, reflect)
User stating commitment → Background Ingestion (record, align, remember)


There is no overlap in responsibility.

What this system explicitly avoids

Auto-creating tasks from vague intent

Interrupting reflection to confirm obvious commitments

Silent planner writes without clear structure

A single “planner” that tries to do everything

One-line summary (use this verbatim if needed)

Sakhi plans in conversation without committing — and commits in the background without interrupting.

How planner outputs are used later

The artifacts produced by the planner contracts have clear downstream consumers:

planned_items (tasks/actions)

Drive the planner UI

Power task lists, status, prioritization, and execution views

Serve as the authoritative source for user-facing actions

Planner goals and milestones

Feed planner summary and stack endpoints

Enable structured overviews (what the user is working toward, not just what they need to do)

Planner context cache

Supports fast planner reads and summaries without recomputing structure

Used by planner APIs and background summarization

Rhythm–planner alignment

Planner outputs are read by rhythm alignment logic

Enables later guidance about fit between planned work and energy patterns

Does not reschedule tasks automatically

Reinforcing design intent

Planner persistence creates execution structure — not instruction.
Other systems may reference planner state, but they do not override it.

This keeps:

planning authoritative

rhythm advisory

reflection interpretive
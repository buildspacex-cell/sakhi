Presence, Reflection & Introspection Workers

(Continuity, Learning, and Self-Correction Layer)

Purpose of this layer

This layer ensures that reflections are not one-off outputs, but part of an ongoing reflective relationship that learns from:

time

user response

tone shifts

repetition

bias

It governs how Sakhi follows up, adapts, and self-corrects around reflection — without interfering with live turns.

When these workers run

Triggered asynchronously by:

reflection generation

scheduled jobs

periodic review loops

Never block the live turn

Operate on existing reflections, feedback, and memory

This layer is post-reflection, not reactive.

presence_reflector

(Continuity & Gentle Follow-Ups)

Why it exists

To maintain reflective continuity over time instead of dropping insights and moving on.

What it does

Finds reflections older than ~5 days

Reads their associated emotional tone annotations

Prompts an LLM to draft 1–2 tone-matched follow-up prompts

How it works

Inserts generated prompts into:

presence_prompts


Each prompt includes a scheduled time for delivery

How it’s used

Presence delivery systems surface these prompts later

Enables “checking back” without nagging or urgency

Reflection is treated as a conversation, not a statement.

reflective_loop

(User Feedback & Memory Relevance Adjustment)

Why it exists

To understand how the user actually responded to reflections and adjust memory strength accordingly.

What it does

For each recent reflection:

Collects subsequent user turns

Uses an LLM to classify:

feedback_type (positive / neutral / negative)

relevance_score

How it works

Writes results into:

reflection_feedback


Averages relevance scores

Nudges:

memory_edges.relevance

How it’s used

Influences which memories are emphasized in future recall

Prevents irrelevant reflections from gaining weight

Memory strength is earned through response, not inference.

reinforcement_calibration

(Reflection Style Learning)

Why it exists

To adapt reflection style based on what actually helps the user.

What it does

Combines:

reflection feedback

emotional tone before/after reflections

Computes a reward score per reflection

How it works

Writes reward signals into:

reflection_scores


Prompts an LLM to adjust calibration traits:

reflection_depth

tone_warmth

conciseness

adaptability

confidence

Updates:

calibration_profile

How it’s used

Guides tuning parameters for future reflection generation

Enables gradual personalization without abrupt shifts

Reflection quality is tuned by outcomes, not preferences alone.

meta_audit

(Bias & Quality Self-Review)

Why it exists

To detect systemic bias or degradation in reflection quality.

What it does

Reviews recent reflections

Uses an LLM to flag:

over-positivity

repetition

missing perspectives

Suggests a correction note

How it works

Writes into:

meta_audit


bias_detected

correction_note

confidence

How it’s used

Correction notes can steer future reasoning

Acts as a guardrail against drift

The system reviews itself so the user doesn’t have to.

tone_analyzer

(Emotional & Tonal Attribution)

Why it exists

To make emotional tone explicit and usable across systems.

What it does

For each reflection, an LLM labels:

dominant_emotion

tone_style

polarity

energy_level

How it works

Writes into:

emotional_tones

How it’s used

Feeds:

presence_reflector (tone matching)

reinforcement_calibration (tone shift detection)

analytics and audits

Tone is treated as data, not intuition.

persona_updater

(Conversational Style Evolution)

Why it exists

To keep Sakhi’s style attuned to the user, not fixed.

What it does

Samples recent user + assistant turns

Uses an LLM to infer:

tone_bias

expressiveness

humor

reflectiveness

warmth

How it works

Blends inferred traits with existing ones

Updates:

persona_traits

How it’s used

Influences tone and style in future responses

Keeps interaction feeling natural and aligned

Persona evolves from interaction, not configuration.

soul_reasoner

(Cross-Theme & Identity Synthesis)

Why it exists

To integrate reflection, rhythm, and themes into deeper identity-level understanding.

What it does

Pulls:

rhythm_insights

reflections

journal_themes

Uses an LLM to infer:

cross-theme links

theme states

higher-order insights

How it works

Writes into:

theme_links
theme_states
insights

How it’s used

Feeds soul / identity snapshots

Supports long-horizon narrative and alignment features

Identity emerges at the intersection of rhythm, reflection, and repetition.

What this layer does not do

Does not interrupt live turns

Does not create goals or actions

Does not overwrite memory

Does not assert identity claims directly

Does not optimize for engagement metrics

This is a learning and continuity layer, not an execution layer.

Core storyline anchor (add this to your spine)

Reflections don’t end when they’re written.
They are followed up, evaluated, corrected, and integrated over time.

One-line summary

This layer helps Sakhi learn how to reflect — not just what to say.
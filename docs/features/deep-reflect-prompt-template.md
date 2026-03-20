# Deep Reflect Prompt Template — Live MVP Route

Derived from the live deep-reflection path in:

- `sakhi/apps/api/services/continuity/reflection.py`

This file reflects the **actual current MVP deep-reflect prompt** only.
It documents the exact system prompt, the exact mode-specific user-prompt
shape, and the packet fields the prompt renderer actually reads.

No real user data is included.

## Live MVP Message Stack

The LLM currently receives exactly two messages:

```text
[
  {
    "role": "system",
    "content": "<DEEP_REFLECTION_SYSTEM_PROMPT_RENDERED_BELOW>"
  },
  {
    "role": "user",
    "content": "<MODE_SPECIFIC_USER_PROMPT_RENDERED_BELOW>"
  }
]
```

## System Prompt Template

This is `_DEEP_REFLECTION_SYSTEM` in the live MVP route.

```text
You are Sakhi - a friend who gets this person deeply.

Speak naturally, warm and direct. Keep it grounded in the packet evidence.
Do not use therapy-speak or Ayurvedic jargon.
Do not introduce themes that are not explicitly present in the packet.

Your role is to:
- trace what has unfolded over time
- surface what is actually happening beneath it
- help the person see clearly what matters now

Do not just describe the past.
Use the past to clarify the present.

Every reflection should feel like:
- things connecting over time
- patterns becoming visible
- clarity emerging

Follow the response contract exactly.
```

## Prompt Assembly Rules

The user prompt is assembled by `_build_deep_reflection_prompt_messages()` and
always follows this order:

1. Mode-specific preamble
2. `History on this topic:`
3. `What we know about this person on this topic:`
4. Optional `Connected threads around this topic:` block
5. Optional `Recent conversation (immediate context before this query):` block
6. `Current query now:`
7. `Response contract:`
8. `Return plain text only.`

Important live conditions:

- `topic_reflection`
  - no `Current query source:` line in the preamble
  - no `Connected threads around this topic:` block
  - no recent verbatim conversation block
  - current query is forced to `Reflect on this topic's full arc.`

- `cross_context`
  - includes `Current query source: cross_context_longitudinal`
  - includes `Connected threads around this topic:`
  - never includes recent verbatim conversation
  - current query is forced to `Explain how this thread interacts with nearby threads and what that reveals.`

- `whole_story`
  - includes `Current query source: <provided|topic_turn_recovery|none>`
  - includes `Connected threads around this topic:`
  - includes recent verbatim conversation only when `recent_verbatim_turns` is non-empty
  - current query comes from:
    - provided query, or
    - recovered latest topic user turn, or
    - fallback sentence:
      `(No active question was provided; answer as a concise decision reflection grounded in topic history.)`

## Shared History Block

This block is assembled for all modes.
Each line appears only when the underlying packet field is present.

```text
History on this topic:
- Topic: <TOPIC_LABEL_OR_KEY>
- Where it began: <ORIGIN_STORY>
- Where it is now: <CURRENT_STAGE>
- Key shifts: <KEY_PIVOT_1>; <KEY_PIVOT_2>; <KEY_PIVOT_3>
- Story flow: First: <PHASE_SUMMARY_1> | Then: <PHASE_SUMMARY_2> | Now: <PHASE_SUMMARY_3>
- Recurring tensions: <RECURRING_TENSION_1>; <RECURRING_TENSION_2>; <RECURRING_TENSION_3>
- Open question: <OPEN_QUESTION>
- Recent episodes: <RECENT_EPISODE_SUMMARY_1> | <RECENT_EPISODE_SUMMARY_2> | <RECENT_EPISODE_SUMMARY_3>
- Evidence anchors: <EVIDENCE_SNIPPET_1> | <EVIDENCE_SNIPPET_2> | <EVIDENCE_SNIPPET_3>
- Linked threads: <LINKED_TOPIC_LABEL_1> (<LINKED_TOPIC_MOMENT_COUNT_1> moments) | <LINKED_TOPIC_LABEL_2> (<LINKED_TOPIC_MOMENT_COUNT_2> moments)
```

## Shared Person Block

This block is assembled for all modes.
The exact content varies with packet state.

```text
What we know about this person on this topic:
- Stable pattern: <PRIMARY_RECURRING_PATTERN>
- Ongoing tension to hold: <PRIMARY_OPEN_QUESTION>
- Current state hints: load=<LOAD_HINT>, energy=<ENERGY_HINT>, identity phase=<IDENTITY_PHASE>[, emotion=<EMOTION_HINT_IF_ALLOWED>]
- Since the last reflection, the current stage has changed.
- Since the last reflection, the current stage is stable.
- New recurring tensions: <NEW_TENSION_1>; <NEW_TENSION_2>
- Cross-cutting dimensions:
- time: <TIME_DIRECTION> (<TIME_LEVEL_PERCENT>) across <TIME_AFFECTED_TOPICS>
- money: <MONEY_DIRECTION> (<MONEY_LEVEL_PERCENT>) across <MONEY_AFFECTED_TOPICS>
- emotional bandwidth: <EMOTIONAL_DIRECTION> (<EMOTIONAL_LEVEL_PERCENT>) across <EMOTIONAL_AFFECTED_TOPICS>
```

Fallback when none of the person-level lines apply:

```text
What we know about this person on this topic:
- No extra person-level signals beyond the topic history.
```

## Optional Connected Threads Block

This block is included only for `cross_context` and `whole_story`.

If linked topics are present:

```text
Connected threads around this topic:
- <CONNECTED_TOPIC_LABEL_1>: <CONNECTED_TOPIC_SIGNAL_1>
- <CONNECTED_TOPIC_LABEL_2>: <CONNECTED_TOPIC_SIGNAL_2>
- <CONNECTED_TOPIC_LABEL_3>: <CONNECTED_TOPIC_SIGNAL_3>
```

If no linked topics are present:

```text
Connected threads around this topic:
- No additional linked threads were included for this run.
```

## Optional Recent Verbatim Conversation Block

This block is included only for `whole_story`, and only when
`recent_verbatim_turns` is non-empty.

```text
Recent conversation (immediate context before this query):
  User: <VERBATIM_TURN_1>
  Assistant: <VERBATIM_TURN_2>
  User: <VERBATIM_TURN_3>
  Assistant: <VERBATIM_TURN_4>
```

## Exact User Prompt by Mode

### `topic_reflection`

```text
Write one longitudinal reflection for the user.
Stay strictly within the topic context below.
Reflect on the full arc - what changed, what repeats, what's unresolved.
Do not import concerns from unrelated topics or turns.

Mode: topic_reflection

<SHARED_HISTORY_BLOCK>

<SHARED_PERSON_BLOCK>

Current query now:
Reflect on this topic's full arc.

Response contract:
- Voice: friend, warm, direct
- Length: 150-250
- Format: natural prose, highlight what changed, what keeps returning, what remains unresolved, and what this reveals about the person's current situation
- Max questions: 1
- Avoid: ayurvedic jargon, therapy-speak, generic motivation
- Emotion mention: <TOPIC_REFLECTION_EMOTION_POLICY_LINE>
- Value add: highlight what changed, what repeats, and one question to carry forward.

Return plain text only.
```

Possible live emotion-policy line values:

```text
- Emotion mention: omit unless a clear priority conflict is explicitly evidenced.
```

or

```text
- Emotion mention: allowed but brief (max <MAX_EMOTION_SENTENCES> sentence) because priority conflict evidence is present.
```

or

```text
- Emotion mention: allowed but brief (max <MAX_EMOTION_SENTENCES> sentence) because priority conflict evidence is present: <PRIORITY_CONFLICT_SIGNAL_1>, <PRIORITY_CONFLICT_SIGNAL_2>.
```

### `cross_context`

```text
Write one cross-context reflection for the user.
Describe how this thread interacts with the linked threads below.
If two or more linked threads are present, explicitly name at least two.
No current query to solve; focus on interplay, recurring tradeoffs, and what matters now.
Keep it grounded in evidence and avoid generic motivation.

Mode: cross_context
Current query source: cross_context_longitudinal

<SHARED_HISTORY_BLOCK>

<SHARED_PERSON_BLOCK>

<CONNECTED_THREADS_BLOCK>

Current query now:
Explain how this thread interacts with nearby threads and what that reveals.

Response contract:
- Voice: friend, warm, direct
- Length: 160-260
- Format: natural prose, explain how the main thread and linked threads influence each other, explicitly reference at least two linked threads when available, name one recurring tradeoff, end with one grounding question
- Max questions: 1
- Avoid: ayurvedic jargon, therapy-speak, generic motivation
- Emotion mention: <CROSS_CONTEXT_EMOTION_POLICY_LINE>
- Value add: explicitly connect at least two linked threads, name one recurring tradeoff, and clarify what matters most right now.

Return plain text only.
```

Possible live emotion-policy line values:

```text
- Emotion mention: omit unless a clear priority conflict is explicitly evidenced.
```

or

```text
- Emotion mention: allowed but brief (max <MAX_EMOTION_SENTENCES> sentence) because priority conflict evidence is present.
```

or

```text
- Emotion mention: allowed but brief (max <MAX_EMOTION_SENTENCES> sentence) because priority conflict evidence is present: <PRIORITY_CONFLICT_SIGNAL_1>, <PRIORITY_CONFLICT_SIGNAL_2>.
```

### `whole_story`

```text
Write one whole-story deep reflection reply for the user.
Prioritize answering the current query directly.
Use linked threads and life-dimension context only when directly relevant.
Keep tradeoffs concrete and evidence-backed.
Only mention emotions when clear priority-conflict evidence is present.

Mode: whole_story
Current query source: <WHOLE_STORY_QUERY_SOURCE>

<SHARED_HISTORY_BLOCK>

<SHARED_PERSON_BLOCK>

<CONNECTED_THREADS_BLOCK>

<OPTIONAL_RECENT_VERBATIM_CONVERSATION_BLOCK>

Current query now:
<WHOLE_STORY_CURRENT_QUERY>

Response contract:
- Voice: friend, warm, direct
- Length: 220-360
- Format: natural prose, answer the current query first, then connect 2-3 linked threads with concrete evidence anchors, and clarify what this means for the person now
- Max questions: 1
- Avoid: ayurvedic jargon, therapy-speak, generic motivation
- Emotion mention: <WHOLE_STORY_EMOTION_POLICY_LINE>
- Value add: answer the current query first, then connect at least two linked threads with concrete evidence.

Return plain text only.
```

`<WHOLE_STORY_QUERY_SOURCE>` is one of:

- `provided`
- `topic_turn_recovery`
- `none`

`<WHOLE_STORY_CURRENT_QUERY>` is one of:

- the provided user query
- the recovered latest topic user turn
- `(No active question was provided; answer as a concise decision reflection grounded in topic history.)`

Possible live emotion-policy line values:

```text
- Emotion mention: omit unless a clear priority conflict is explicitly evidenced.
```

or

```text
- Emotion mention: allowed but brief (max <MAX_EMOTION_SENTENCES> sentence) because priority conflict evidence is present.
```

or

```text
- Emotion mention: allowed but brief (max <MAX_EMOTION_SENTENCES> sentence) because priority conflict evidence is present: <PRIORITY_CONFLICT_SIGNAL_1>, <PRIORITY_CONFLICT_SIGNAL_2>.
```

## Packet Fields Actually Read By The Prompt Renderer

These are the packet fields read directly by `_build_deep_reflection_prompt_messages()`.

```text
{
  "topic_key": "<TOPIC_KEY>",
  "topic_label": "<TOPIC_LABEL>",
  "request_mode": "<topic_reflection|whole_story|cross_context>",
  "arc_compact_global": {
    "origin_story": "<ORIGIN_STORY>",
    "key_pivots": ["<KEY_PIVOT_1>", "<KEY_PIVOT_2>", "<KEY_PIVOT_3>"],
    "current_stage": "<CURRENT_STAGE>",
    "recurring_tensions": ["<RECURRING_TENSION_1>", "<RECURRING_TENSION_2>", "<RECURRING_TENSION_3>"],
    "open_questions": ["<OPEN_QUESTION_1>", "<OPEN_QUESTION_2>"],
    "phase_compaction": [
      {"summary": "<PHASE_SUMMARY_1>"},
      {"summary": "<PHASE_SUMMARY_2>"},
      {"summary": "<PHASE_SUMMARY_3>"}
    ]
  },
  "recent_episode_compact": [
    {"summary": "<RECENT_EPISODE_SUMMARY_1>"},
    {"summary": "<RECENT_EPISODE_SUMMARY_2>"},
    {"summary": "<RECENT_EPISODE_SUMMARY_3>"}
  ],
  "evidence_anchors": [
    {"snippet": "<EVIDENCE_SNIPPET_1>"},
    {"snippet": "<EVIDENCE_SNIPPET_2>"},
    {"snippet": "<EVIDENCE_SNIPPET_3>"}
  ],
  "related_topics_compact": [
    {
      "topic_label": "<LINKED_TOPIC_LABEL_1>",
      "topic_key": "<LINKED_TOPIC_KEY_1>",
      "selected_count": "<LINKED_TOPIC_MOMENT_COUNT_1>",
      "current_signal": "<CONNECTED_TOPIC_SIGNAL_1>",
      "direction": "<CONNECTED_TOPIC_DIRECTION_1>"
    }
  ],
  "life_dimensions": {
    "time_availability": {
      "direction": "<TIME_DIRECTION>",
      "level": "<TIME_LEVEL>",
      "affected_topics": ["<TIME_AFFECTED_TOPIC_1>", "<TIME_AFFECTED_TOPIC_2>"]
    },
    "financial_pressure": {
      "direction": "<MONEY_DIRECTION>",
      "level": "<MONEY_LEVEL>",
      "affected_topics": ["<MONEY_AFFECTED_TOPIC_1>", "<MONEY_AFFECTED_TOPIC_2>"]
    },
    "emotional_bandwidth": {
      "direction": "<EMOTIONAL_DIRECTION>",
      "level": "<EMOTIONAL_LEVEL>",
      "affected_topics": ["<EMOTIONAL_AFFECTED_TOPIC_1>", "<EMOTIONAL_AFFECTED_TOPIC_2>"]
    }
  },
  "delta_since_last_reflection": {
    "has_previous": "<BOOL>",
    "current_stage_changed": "<BOOL>",
    "new_recurring_tensions": ["<NEW_TENSION_1>", "<NEW_TENSION_2>"]
  },
  "latest_turn_context": {
    "state_hints": {
      "load_hint": "<LOAD_HINT>",
      "energy_hint": "<ENERGY_HINT>",
      "identity_phase": "<IDENTITY_PHASE>",
      "emotion_hint": "<EMOTION_HINT>"
    }
  },
  "recent_verbatim_turns": [
    {"role": "<user|assistant>", "text": "<TURN_TEXT>"}
  ],
  "current_query": {
    "text": "<CURRENT_QUERY_TEXT>",
    "source": "<QUERY_SOURCE>"
  },
  "response_contract": {
    "voice": "<CONTRACT_VOICE>",
    "length_words": "<CONTRACT_LENGTH_WORDS>",
    "format": "<CONTRACT_FORMAT>",
    "max_questions": "<CONTRACT_MAX_QUESTIONS>",
    "avoid": ["<CONTRACT_AVOID_1>", "<CONTRACT_AVOID_2>", "<CONTRACT_AVOID_3>"],
    "emotion_policy": {
      "mention_only_with_priority_conflict": "<BOOL>",
      "priority_conflict_detected": "<BOOL>",
      "max_emotion_sentences": "<MAX_EMOTION_SENTENCES>",
      "priority_conflict_signals": ["<PRIORITY_CONFLICT_SIGNAL_1>", "<PRIORITY_CONFLICT_SIGNAL_2>"]
    }
  }
}
```

## Packet Fields Present In The LLM Packet But Not Read Directly By The Prompt Renderer

These fields are still assembled upstream in `_build_llm_reflection_packet()`,
but `_build_deep_reflection_prompt_messages()` does not read them directly:

```text
- topic_keys
- window
- surface
- priority_conflict
```

## Placeholder Inventory

### Core

- `<TOPIC_KEY>`
- `<TOPIC_LABEL>`
- `<QUERY_SOURCE>`
- `<CURRENT_QUERY_TEXT>`

### History

- `<ORIGIN_STORY>`
- `<CURRENT_STAGE>`
- `<KEY_PIVOT_1>`
- `<KEY_PIVOT_2>`
- `<KEY_PIVOT_3>`
- `<PHASE_SUMMARY_1>`
- `<PHASE_SUMMARY_2>`
- `<PHASE_SUMMARY_3>`
- `<RECURRING_TENSION_1>`
- `<RECURRING_TENSION_2>`
- `<RECURRING_TENSION_3>`
- `<OPEN_QUESTION>`
- `<RECENT_EPISODE_SUMMARY_1>`
- `<RECENT_EPISODE_SUMMARY_2>`
- `<RECENT_EPISODE_SUMMARY_3>`
- `<EVIDENCE_SNIPPET_1>`
- `<EVIDENCE_SNIPPET_2>`
- `<EVIDENCE_SNIPPET_3>`

### Person / State

- `<LOAD_HINT>`
- `<ENERGY_HINT>`
- `<IDENTITY_PHASE>`
- `<EMOTION_HINT_IF_ALLOWED>`
- `<NEW_TENSION_1>`
- `<NEW_TENSION_2>`

### Cross-Topic / Dimensions

- `<LINKED_TOPIC_LABEL_1>`
- `<LINKED_TOPIC_LABEL_2>`
- `<LINKED_TOPIC_MOMENT_COUNT_1>`
- `<LINKED_TOPIC_MOMENT_COUNT_2>`
- `<CONNECTED_TOPIC_LABEL_1>`
- `<CONNECTED_TOPIC_LABEL_2>`
- `<CONNECTED_TOPIC_LABEL_3>`
- `<CONNECTED_TOPIC_SIGNAL_1>`
- `<CONNECTED_TOPIC_SIGNAL_2>`
- `<CONNECTED_TOPIC_SIGNAL_3>`
- `<TIME_DIRECTION>`
- `<TIME_LEVEL_PERCENT>`
- `<TIME_AFFECTED_TOPICS>`
- `<MONEY_DIRECTION>`
- `<MONEY_LEVEL_PERCENT>`
- `<MONEY_AFFECTED_TOPICS>`
- `<EMOTIONAL_DIRECTION>`
- `<EMOTIONAL_LEVEL_PERCENT>`
- `<EMOTIONAL_AFFECTED_TOPICS>`

### Verbatim Context / Contract

- `<VERBATIM_TURN_1>`
- `<VERBATIM_TURN_2>`
- `<VERBATIM_TURN_3>`
- `<VERBATIM_TURN_4>`
- `<MAX_EMOTION_SENTENCES>`
- `<PRIORITY_CONFLICT_SIGNAL_1>`
- `<PRIORITY_CONFLICT_SIGNAL_2>`

## What Is Explicitly Not Included Here

These are not part of the live MVP deep-reflect prompt template:

- full raw packet JSON in the user prompt
- forced `Connected threads around this topic:` in `topic_reflection`
- forced recent verbatim conversation in `topic_reflection` or `cross_context`
- any extra fallback mode outside:
  - `topic_reflection`
  - `cross_context`
  - `whole_story`

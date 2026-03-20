# Deep Reflect & Soul Screen Contract

> **Status:** Locked (2026-03-15)
> **Purpose:** Define all four user-facing features, their backend modes, what each builds, and how they differ.

---

## Feature → Backend Mode Map

| Frontend Feature | Backend Mode | Screen | Route | Query |
|---|---|---|---|---|
| Normal Chat | — | Chat screen | `POST /v2/turn` | User's message drives the reply |
| Deep Reflect | `whole_story` | Chat screen | `POST /continuity/reflection/run` | Required — user's typed question |
| `<Topic> Story` | `topic_reflection` | Soul screen | `POST /continuity/reflection/run` | None |
| My Story | `cross_context` | Soul screen | `POST /continuity/reflection/run` | None |

This mapping is the authoritative reference. Use frontend names when talking about the product. Use backend modes when talking about the API or code.

---

## What Each Feature Is

**Normal Chat** — The standard conversation. Sakhi replies to what the user says, grounded by the continuity pack (topic arc + journal evidence). Synchronous, < 3s.

**Deep Reflect** — A chat feature. The user types a question, taps Deep Reflect, and gets a synthesis that answers that question using the full arc of the active topic woven with a correlated second thread. Appears in chat as a distinct element (not a normal bubble). Async, 5–30s.

**`<Topic> Story`** — A Soul screen feature. No query. Traces the full longitudinal arc of a single topic - what changed, what keeps returning, what remains unresolved, and what that reveals about the person's current situation. The user opens the Soul screen, selects a topic, and reads the arc.

**My Story** — A Soul screen feature. No query. Synthesises the interplay across active topic threads - explicitly connecting linked threads, naming one recurring tradeoff, and clarifying what matters most right now. The user opens the Soul screen My Story section.

**The core distinction:**
- Chat features (Normal Chat, Deep Reflect) = part of a conversation, user is asking something
- Soul screen features (`<Topic> Story`, My Story) = standalone reflection cards, no conversation, no query

---

## Readiness Gates

### Deep Reflect (`whole_story`)

The Deep Reflect button appears in chat only when all of the following are true:

1. **Topic active** — `continuity.topic_key` present in the `/v2/turn` response
2. **mirror_allowed** — governance permits mirroring this topic
3. **detail_allowed** — topic has sufficient detail surface permission
4. **selected_count >= 8** — at least 8 evidence moments in the primary topic arc
5. **cross_context ready** — a correlated topic exists with combined_score >= 0.35 and >= 6 moments
6. **whole_story thresholds** — primary >= 8 moments, related >= 6 moments, total >= 12
7. **User has typed a query** — `latestUserMessage.trim().length > 0` (client-side gate)

If the gate fails, the button does not appear. A status hint tells the user why.

**Single-topic reflection is not surfaced in chat.** A user with only one thread uses `<Topic> Story` on the Soul screen instead.

### `<Topic> Story` and My Story (`topic_reflection` / `cross_context`)

- **`<Topic> Story`**: `selected_count >= 3` (`MIN_TOPIC_STORY_MOMENTS`) — matches backend `min_len=3`
- **My Story**: eligible related topics must each have `selected_count >= 6` (`MIN_RELATED_TOPIC_MOMENTS`) — matches backend `cross_context_min_moments=6`; requires >= 2 such topics (`myStoryReady`)
- `mirror_allowed` must be true for all topics
- No query required

---

## What Gets Built (Packet)

All three reflection features (`whole_story`, `topic_reflection`, `cross_context`) share the same assembly function — `_build_reflection_llm_packet` in `services/continuity/reflection.py` — with field availability varying by mode.

| Field | Source | Deep Reflect | `<Topic> Story` | My Story |
|---|---|---|---|---|
| `arc_compact_global` | Full arc: origin story, key pivots, recurring tensions, current stage, open questions | ✓ | ✓ | ✓ |
| `evidence_anchors` | Journal moments by temporal spread — early + middle + late across arc timeline, up to 8 | ✓ | ✓ | ✓ |
| `recent_episode_compact` | `memory_episodic` daily episode summaries (worker-produced), up to 3 | ✓ | ✓ | ✓ |
| `related_topics_compact` | Full arcs of correlated topics, up to 3 | ✓ | — | ✓ |
| `life_dimensions` | `continuity_life_dimensions` cache: time/money/emotional bandwidth | ✓ | — | ✓ |
| `delta_since_last_reflection` | What changed in the arc since the last reflection run | ✓ | ✓ | ✓ |
| `recent_verbatim_turns` | Last 4 conversation turns (user + assistant) verbatim, no topic filtering — immediate context that shaped the query | ✓ | — | — |
| `latest_turn_context` | Last user message on this topic, recovered from session history (topic-keyword filtered) | ✓ | — | — |
| `current_query` | Provided `user_query` or recovered turn message | ✓ | — | — |
| `response_contract` | Format/length/voice rules per mode | ✓ | ✓ | ✓ |

**What Deep Reflect adds over Normal Chat:**
- `recent_episode_compact` — captures conversations that were never journalled. Normal Chat never touches `memory_episodic`.
- `related_topics_compact` — full arcs of correlated topics, not just a one-line signal.
- `life_dimensions` — integrated into synthesis, not just surface signals.
- `delta_since_last_reflection` — what changed since the user last ran Deep Reflect.

**What Deep Reflect drops that Normal Chat has:**
- Full verbatim last 8 turns — replaced by last 4 verbatim turns (immediate context) + episodic summaries (broader longitudinal view).
- Session summary — not loaded.
- Keyword-ranked evidence — uses temporal spread (early + middle + late) instead of keyword overlap with the current message.

**Deep Reflect is not a superset of Normal Chat.** It trades immediate conversational context for the full longitudinal picture.

**Dependency:** `recent_episode_compact` is empty if the `episodic_consolidation_v21` worker has not run.

---

## Response Contracts

| Frontend Feature | Backend Mode | Length | Format |
|---|---|---|---|
| Deep Reflect | `whole_story` | 220–360 words | Answer the current query first, connect 2–3 linked threads with concrete evidence anchors, and clarify what this means for the person now |
| `<Topic> Story` | `topic_reflection` | 150–250 words | Highlight what changed, what keeps returning, what remains unresolved, and what this reveals about the person's current situation |
| My Story | `cross_context` | 160–260 words | Explicitly connect at least two linked threads, name one recurring tradeoff, and clarify what matters most right now |

**Emotion policy (all modes):** Mention emotion only when a priority conflict is evidenced (time/money/commitment tradeoff detectable in the arc). Otherwise stay tactical and evidence-grounded.

**Voice (all modes):** Friend, warm, direct. No Ayurvedic jargon. No therapy-speak. No generic motivation.

---

## How All Four Features Compare

| Capability | Normal Chat | Deep Reflect | `<Topic> Story` | My Story |
|---|---|---|---|---|
| Backend mode | — (`/v2/turn`) | `whole_story` | `topic_reflection` | `cross_context` |
| Screen | Chat | Chat | Soul | Soul |
| Has a query | Yes — conversational | Yes — drives synthesis | No | No |
| Topic arc | As grounding context | As primary output | As primary output | All active topics |
| Journal evidence | Up to 8 moments, keyword-ranked | Up to 8 moments, temporal spread | Up to 8 moments, temporal spread | Up to 8 moments, temporal spread |
| Recent verbatim turns | Last 8 turns | Last 4 turns (immediate context) | — | — |
| Episodic memory | No | Yes — `memory_episodic` | Yes — `memory_episodic` | Yes — `memory_episodic` |
| Delta since last reflection | No | Yes | Yes | Yes |
| Cross-thread synthesis | Signal only (one line) | Full narrative — primary + correlated thread | No — single topic | Full — all active threads |
| Life dimensions | Signal only | Integrated | Not included | Integrated |
| Response form | Conversational reply, 60–120 words | Query answer as synthesis, 220–360 words | Arc trace, 150–250 words | Thread interplay, 160–260 words |
| Render | Chat bubble | Distinct element in chat | Reflection card, Soul screen | Reflection card, Soul screen |
| Latency | Synchronous, < 3s | Async, 5–30s | Async, 5–30s | Async, 5–30s |
| Cross-topic gate | No | Yes — `whole_story.ready` | No | Yes — >= 2 eligible topics |

---

## Async Architecture (Deep Reflect, `<Topic> Story`, My Story)

1. `POST /continuity/reflection/run` — enqueues job, returns `{ reflection_id, status: "queued" }`
2. RQ worker runs `_build_reflection_llm_packet` + LLM call
3. Client polls `GET /continuity/reflection/status?id={id}` every 2s (up to 70 polls = 140s timeout)
4. When `status: "done"`, client fetches `GET /continuity/reflection/result?id={id}`

Normal Chat is synchronous via `POST /v2/turn` — no polling.

---

## UI Contract (Mobile)

**Deep Reflect (chat screen):**
- Button appears only when `deepAnswerReady = true` (all gates passed)
- Status hint tells the user why it's locked when gates fail
- Topic label shown as context: "Deep Reflect on: Work Decisions"
- Result appears as a distinct element in chat (not a normal bubble)

**`<Topic> Story` and My Story (Soul screen):**
- Standalone reflection cards, not part of any conversation
- `<Topic> Story`: triggered by selecting a topic arc and tapping Reflect
- My Story: triggered from the My Story section; requires `myStoryReady` (>= 2 eligible topics)

---

## Key Constraints

- All reflection features require journalling history. Without journal entries the compiler has no moments, thresholds will not be met.
- `recent_episode_compact` is empty if the `episodic_consolidation_v21` worker has not run.
- Deep Reflect requires cross-topic correlation — a second active thread must exist with sufficient overlap. Single-topic users see the button locked; their arc is available as `<Topic> Story` on the Soul screen.
- Governance (`mirror_allowed`, `detail_allowed`) can block any reflection feature independently of arc depth.

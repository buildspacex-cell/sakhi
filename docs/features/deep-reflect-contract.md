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

**Deep Reflect** — A chat feature. The user types a question, taps Deep Reflect, and gets a synthesis that answers that question using the full arc of the active topic, weaving in a correlated second thread when one is clearly available. Appears in chat as a distinct element (not a normal bubble). Async, 5–30s.

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
4. **effective_selected_count >= 8** — at least 8 effective same-thread moments in the active topic arc (strict primary moments + thread-attached follow-ups; related cross-topic projections do not count)
5. **User has typed a query** — `latestUserMessage.trim().length > 0` (client-side gate)

If the gate fails, the button does not appear. A status hint tells the user why.

**Linked-thread context is additive, not mandatory.** If `continuity.whole_story.ready` is true, Deep Reflect weaves in the linked thread(s). If not, it still runs as a strong single-topic deep reflection on the active thread.

### `<Topic> Story` and My Story (`topic_reflection` / `cross_context`)

- **`<Topic> Story`**: `selected_count >= 3` (`MIN_TOPIC_STORY_MOMENTS`) — matches backend `min_len=3`
- **My Story**: eligible related topics must each have `selected_count >= 6` (`MIN_RELATED_TOPIC_MOMENTS`) — matches backend `cross_context_min_moments=6`; requires >= 2 such topics (`myStoryReady`)
- `mirror_allowed` must be true for all topics
- No query required

**Continuity depth semantics**
- `primary_selected_count` = explicit primary-anchor moments only
- `attached_selected_count` = thread-aware follow-up moments attached after second-pass resolution
- `effective_selected_count` = `primary_selected_count + attached_selected_count`
- `related_selected_count` = projected linked-topic overlap; does not count toward chat Deep Reflect readiness

---

## What Gets Built (Packet)

All three reflection features (`whole_story`, `topic_reflection`, `cross_context`) share the same assembly function — `_build_reflection_llm_packet` in `services/continuity/reflection.py` — with field availability varying by mode.

| Field | Source | Deep Reflect | `<Topic> Story` | My Story |
|---|---|---|---|---|
| `arc_compact_global` | Full arc: origin story, key pivots, recurring tensions, current stage, open questions | ✓ | ✓ | ✓ |
| `evidence_anchors` | Journal moments by temporal spread — early + middle + late across arc timeline, up to 8 | ✓ | ✓ | ✓ |
| `recent_episode_compact` | `memory_episodic` daily episode summaries (worker-produced), up to 3 | ✓ | ✓ | ✓ |
| `related_topics_compact` | Full arcs of correlated topics, up to 3 | Optional — when linked threads are available | — | ✓ |
| `life_dimensions` | `continuity_life_dimensions` cache: time/money/emotional bandwidth | ✓ | — | ✓ |
| `delta_since_last_reflection` | What changed in the arc since the last reflection run | ✓ | ✓ | ✓ |
| `recent_verbatim_turns` | Last 4 conversation turns (user + assistant) verbatim, no topic filtering — immediate context that shaped the query | ✓ | — | — |
| `latest_turn_context` | Last user message on this topic, recovered from session history (topic-keyword filtered) | ✓ | — | — |
| `current_query` | Provided `user_query` or recovered turn message | ✓ | — | — |
| `response_contract` | Format/length/voice rules per mode | ✓ | ✓ | ✓ |

**What Deep Reflect adds over Normal Chat:**
- `recent_episode_compact` — captures conversations that were never journalled. Normal Chat never touches `memory_episodic`.
- `related_topics_compact` — full arcs of correlated topics when linked threads are available, not just a one-line signal.
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
| Deep Reflect | `whole_story` | 220–360 words | Answer the current query first, use linked threads and concrete evidence anchors when they add clarity, and clarify what this means for the person now |
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
| Cross-thread synthesis | Signal only (one line) | Optional — primary thread first, linked thread when available | No — single topic | Full — all active threads |
| Life dimensions | Signal only | Integrated | Not included | Integrated |
| Response form | Conversational reply, 60–120 words | Query answer as synthesis, 220–360 words | Arc trace, 150–250 words | Thread interplay, 160–260 words |
| Render | Chat bubble | Distinct element in chat | Reflection card, Soul screen | Reflection card, Soul screen |
| Latency | Synchronous, < 3s | Async, 5–30s | Async, 5–30s | Async, 5–30s |
| Cross-topic gate | No | Optional linked context via `whole_story.ready` | No | Yes — >= 2 eligible topics |

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
- Deep Reflect no longer requires cross-topic correlation as a hard gate. A linked thread enriches the run when `whole_story.ready` is true, but single-topic deep runs are still allowed once the active thread has enough detail depth.
- Governance (`mirror_allowed`, `detail_allowed`) can block any reflection feature independently of arc depth.

# Continuity Demo — Working Demo Plan

> Internal build document. Last updated: 2026-04-17
> Status: Approved direction. Ready to build.

---

## What This Demo Has to Prove

Not "Sakhi gives better answers than ChatGPT."

**"Sakhi can do something ChatGPT memory structurally cannot."**

This distinction matters for investors. ChatGPT and Claude both have memory features. A side-by-side where Sakhi produces a richer answer to the same question is easy to dismiss — the investor assumes OpenAI will close that gap. The demo has to show something OpenAI *cannot* close: **trajectory intelligence across time, owned by the user, crossing model boundaries.**

The demo is not a quality comparison. It is a capability gap.

---

## The Three Gaps to Demonstrate

Each corresponds to a real investor objection (see `docs/Messaging/competitive-objection-responses.md`):

| Gap | What it shows | Why incumbents can't close it |
|---|---|---|
| **Trajectory** | Sakhi tracks *how* thinking moved, not just what was said | Memory stores facts; arc tracks direction, drift, decision state |
| **Cross-session without manual work** | User never maintained a thread; Sakhi held it anyway | ChatGPT memory is passive fact capture, not active arc compilation |
| **Cross-model** | History persists when model changes | OpenAI memory locked to OpenAI; Anthropic memory locked to Anthropic |

The demo shows all three. Each panel is one gap made visible.

---

## Demo Architecture

### The Scenario — Maya, 21 Days

A founder (Maya) has been thinking about her go-to-market wedge for 3 weeks. She never maintained a thread. She never organised her thinking. She just had conversations — across different sessions, different days, different moods. Today she opens a new session and asks one question.

This is normal user behaviour. No special setup. No thread curation. That's the point.

### The Three Panels

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│   ChatGPT Memory    │    Claude Memory     │       Sakhi         │
│   (fresh session)   │   (fresh session)    │   (Maya's thread)   │
│                     │                      │                     │
│  "Happy to help!    │  "I'd be happy to    │  "You've returned   │
│   Could you share   │   think through      │   to this 9 times.  │
│   some context      │   this with you.     │   Every operator    │
│   about..."         │   What have you      │   call raised your  │
│                     │   explored so far?"  │   conviction. The   │
│                     │                      │   signal is         │
│                     │                      │   consistent."      │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

Left two panels: real ChatGPT API and real Claude API calls — fresh sessions, just the user's question, no history. This is honest. This is what happens when you open a new window today.

Right panel: real Sakhi `turn_v2` call with Maya's demo person_id — 21 days of seeded conversation history, compiled into a live continuity pack at query time.

No staging. No pre-written responses. All three are live API calls made simultaneously when the user submits the question.

---

## Seed Data — Maya's 21-Day History

10 sessions inserted as `journal_entries` with backdated `ts` values. No workers needed — `build_continuity_pack` compiles from raw journal entries inline at query time.

| Day | Entry content |
|---|---|
| Day 1 | "Should I go B2B or B2C? I keep going back and forth. B2B feels right but I'm not sure my network gets me there fast enough." |
| Day 2 | "Thinking about ICP more carefully. Operators seem to have the clearest pain but SMBs have more of them. Volume vs depth." |
| Day 5 | "Had a call with an operator today — a logistics team lead. The workflow pain was visceral. He said he'd pay $200/mo without blinking." |
| Day 7 | "Looked at what competitors charge for SMB. Lower ACV but easier to close. Starting to second-guess operators." |
| Day 9 | "Keep coming back to operators. Every time I try to model SMB the unit economics feel thin. But TAM worries me." |
| Day 12 | "Separate question today — if I go operators, do I charge by seat or by usage? Seat feels predictable, usage feels fair." |
| Day 14 | "Third operator call this week. They pulled hardest every time. SMB prospects asked more questions, converted less." |
| Day 16 | "Thinking about enterprise operators vs SMB operators. Enterprise is slower sales cycle but 10x the contract size." |
| Day 19 | "Pretty sure it's operators. SMB operators, not enterprise. But I keep second-guessing myself on TAM size. What if the market is too small?" |

Day 21 is the live demo session. The user asks the question. All three panels respond in real time.

---

## The Three Pre-Set Demo Questions

Chosen to maximise the contrast on each gap:

**Question 1 — Trajectory**
> *"Where are we on the wedge decision?"*

- ChatGPT / Claude: asks for context
- Sakhi: surfaces 9 sessions, decision arc, consistent signal

**Question 2 — Pattern recognition across time**
> *"What am I second-guessing, and has that changed?"*

- ChatGPT / Claude: cannot answer, no history
- Sakhi: identifies TAM concern appearing on Day 9 and Day 19, flags it as recurring not new

**Question 3 — Synthesis**
> *"What would you tell me to decide this week?"*

- ChatGPT / Claude: gives generic decision framework
- Sakhi: gives a specific answer grounded in 21 days of actual signal

---

## Technical Build Plan

### 1. Seed Endpoint

`POST /demo/continuity/seed` (FastAPI)

- Creates a dedicated demo persona: `DEMO_CONTINUITY_PERSON_ID` (separate from existing `DEMO_USER_ID`)
- Inserts the 10 journal entries with backdated `ts` values (today minus N days)
- Sets `layer = 'conversation'` so continuity compiler treats them as conversation turns
- Enables continuity policy for the person: `upsert_continuity_policy(person_id, enabled=True)`
- Idempotent — deletes and reinserts on repeat calls
- Returns `{person_id, session_count, date_range}`

### 2. Compare Endpoint

`POST /api/demo/continuity/compare` (Next.js route)

Takes `{question, person_id}`, fires three calls in parallel, streams all three back as SSE:

```typescript
const [chatgpt, claude, sakhi] = await Promise.all([
  streamOpenAI(question),          // gpt-4o, no history, just question
  streamAnthropic(question),       // claude-sonnet, no history, just question
  streamSakhi(question, person_id) // proxied turn_v2, full continuity
])
```

Left two: OpenAI and Anthropic SDK calls, single user message, no system context.
Right: proxied to `turn_v2` with `person_id`, standard turn flow, full continuity pack loaded.

SSE stream format:
```
data: {"panel": "chatgpt", "chunk": "Happy to help..."}
data: {"panel": "claude", "chunk": "I'd be happy..."}
data: {"panel": "sakhi", "chunk": "You've returned..."}
data: {"panel": "sakhi", "done": true}
```

### 3. Demo Page

`/company-deck/continuity-demo`

**Layout:**
- Top: "21 days. 9 sessions. One question." — context setter
- Seed button with state: "Load Maya's history" → "Loading..." → "21 days loaded ✓"
- Three equal-width panels with headers:
  - Left: ChatGPT logo · "New session · No prior context"
  - Middle: Claude logo · "New session · No prior context"
  - Right: Sakhi mark · "Continuing from 21 days ago · 9 sessions"
- Three question chips above the input
- Single input field, one submit fires all three simultaneously
- Streaming text in all three panels in real time
- No winner/loser UI — the responses speak for themselves

**Panel header detail:**
- Left two show a small "session history" indicator: empty/blank
- Right shows: `9 sessions · 21 days · Wedge decision thread`

**After response loads:**
- Below Sakhi panel: a collapsed "What Sakhi held" section showing the arc — a small timeline of the 9 sessions with the decision state at each point (questioning → leaning → second-guessing → signal consistent). Expandable. Shows investors the engine, not just the output.

### 4. Reuse Existing Infrastructure

| What | Where | How used |
|---|---|---|
| Demo seed pattern | `/api/demo/simulation/seed` | Copy pattern for new continuity seed route |
| `build_continuity_pack` | `continuity/chat.py` | Called by `turn_v2` — no changes needed |
| `turn_v2` | `routes/turn_v2.py` | Sakhi panel calls this directly |
| `upsert_continuity_policy` | `continuity/adapters.py` | Enable continuity for demo persona |
| `ingest_entry` | `observe/ingest_service.py` | Write backdated journal entries |
| `DEMO_USER_ID` pattern | `tests/fixtures` | Create `DEMO_CONTINUITY_PERSON_ID` constant |

---

## What to Verify Before Building the UI

Insert 5 backdated journal entries for a test person_id manually and call `build_continuity_pack` with the query *"wedge decision"*. Check that the continuity pack surfaces entries with the right anchor, arc direction, and decision states.

If the classifier anchors correctly — build the UI.
If entries aren't surfacing — adjust the seed content to include taxonomy keywords the classifier is looking for (check `SIMULATION_CONTINUITY_TAXONOMY` in `continuity/taxonomy.py`).

This is a 30-minute verification before committing to the full frontend build.

---

## What This Demo Does for the Investor Conversation

| Investor says | Demo shows |
|---|---|
| "ChatGPT has memory" | Left panel has memory on. Still asks for context. Sakhi doesn't. |
| "I'll just keep one thread" | Maya never maintained a thread. 9 separate sessions. Sakhi held them anyway. |
| "OpenAI will build this" | Cross-model panel: Claude and GPT-4o both blank. Sakhi has both. They structurally cannot share. |
| "Show me the engine" | "What Sakhi held" section expands to show the arc timeline — trajectory, not facts. |

The demo does not claim Sakhi writes better prose. It claims Sakhi does something the incumbents structurally cannot. Every panel response proves it live.

---

## Open Questions

- [ ] Should the left two panels show ChatGPT memory *enabled* (more honest, more striking) or disabled? Recommendation: enabled — if memory is on and they still ask for context, the gap is undeniable.
- [ ] Should we show the "What Sakhi held" arc timeline on the one-pager itself, or only in the demo? Recommendation: demo only — the one-pager stays clean.
- [ ] Should users be able to type their own question or only use pre-set ones? Recommendation: both — chips for the demo flow, free input for curious investors.
- [ ] Does the Sakhi panel need a disclaimer that this is a demo persona? Yes — small line: "Demo persona · Not your data."

# Normal Chat Scope — Locked Design

> **Status:** Locked (2026-03-21)
> **Applies to:** `POST /v2/turn` — the standard chat turn path
> **Purpose:** Define exactly what context the LLM receives for a normal chat reply, and what is explicitly out of scope.

---

## What the LLM Receives

The LLM sees exactly five layers, in this order:

### Layer 1 — System Prompt (`build_prompt`)
Built by `conversation_reasoner.py`.

| Block | Content | Condition |
|---|---|---|
| Identity + voice | Sakhi persona, tone rules, word constraints | Always |
| Current state | Tone style, emotion, energy level, mirroring strategy | Always |
| Continuity section | Topic arc: phase path (4 labels), anchor moments (3), decision ledger (6 items), qualitative arc summary, evidence (up to 8 journal snippets) | When continuity pack has an active topic |
| Cross-topic section | Connected thread label + life dimension signals (time/money/emotional bandwidth) | When cross-topic readiness is present |
| Governance guard | Hard constraint block | When governance fires a guard |

**Explicitly removed from system prompt:**
- `build_context_scan()` output (emotion/friction background block) — computed metadata only, not injected into the live lean MVP prompt
- `st_block` (`short_term.texts[-3:]` from `personal_model`) — duplicate of Layer 4, weaker signal (assistant-only, no user turns). Removed.

### Layer 2 — Recall System Message
Injected as a second system message in `conversation_engine.py`.

| Condition | What happens |
|---|---|
| **Topic active** (continuity pack has `topic_key`) | Recall message is **skipped entirely** — continuity pack evidence already covers topic memory. Recall and patterns calls are also skipped at the gather stage (no wasted DB/embedding work). |
| **No topic detected** | Vector-first global recall, `k=5`, recency + diversity weighted. Sources: journal embeddings, reflections, facts, memory nodes. When patterns context exists, it is appended to the same second system message under `Patterns:` |
| **Explicit memory-retrieval intent** (router detects "remember when...", proper noun lookup) | BM25 hybrid recall enabled as escape hatch |

**Explicitly removed from recall:**
- BM25 from default path — only invoked on explicit memory-retrieval intent
- LLM summarisation step inside `build_recall_context` (the `> 800 chars → call_llm` branch) — removed entirely

### Layer 3 — Session Summary
Compressed summary of older turns, injected when `total_turns >= compress_threshold` and a summary exists. Built by background `session_compress` worker.

### Layer 4 — Verbatim Turn History
Last 8 user/assistant pairs as real message roles (`conversation_engine.py:229`). Controlled by `SAKHI_CONVERSATION_RECENT_LIMIT=8`.

### Layer 5 — Current Message
The user's current message as the final `user` role.

---

## What the Continuity Pack Is

The continuity pack (`build_continuity_pack` in `services/continuity/chat.py`) is built as follows:

1. Load all `journal_entries` rows for this person in a **120-day window**
2. The kala compiler (`compile_entries_for_continuity`) groups those raw journal entries into topic arcs with phases — each "moment" is a direct reference to a specific journal entry (`source_ref: "journal:{entry_id}"`)
3. Select the arc matching the current topic anchor
4. `_select_evidence` picks the top 8 moments ranked by: keyword overlap with user message → confidence → recency
5. `_build_history_compact` produces: 4 phase labels (First/Then/Then/Now), 3 anchor moment snippets, 6 decision ledger items, qualitative arc summary

**It is not episodic memory.** The `memory_episodic` table is not touched. It is not aware of recent chat turns unless those turns triggered journal writes.

**It is journal-only.** Facts, memory nodes, and reflections are not in the compiler's input (`adapters.py:212`). Those sources are covered by the Layer 2 global recall fallback when no topic is active.

---

## What Is Explicitly Out of Scope for Normal Chat

These were present in the turn path and have been removed or gated:

| What | Status | Reason |
|---|---|---|
| `rhythm_soul_frame`, `ESR_frame`, `identity_momentum_frame`, `identity_timeline_frame` | Removed from LLM prompt | Ayurveda-era context frames, not continuity-first. Don't improve reply quality. |
| `inner_dialogue` + `nudge_state` | Disabled (env flag `SAKHI_ENABLE_INNER_DIALOGUE=1` to re-enable) | LLM call + DB read. Rarely affects response. |
| `compute_microreg`, `compute_tone`, `compute_empathy` | Fire-and-forget background task | DB writes to personal_model. Available next turn from DB. Not needed for current turn's LLM. |
| `build_context_scan()` prompt block | Removed from live system prompt | Lean MVP prompt keeps state to tone/emotion/energy/mirroring and continuity guidance only. |
| `micro_goals` | Fire-and-forget background task | DB write, side effect only. |
| Recommendations pipeline | Reactive + body-module only (not proactive/contextual/nudge) | LLM call. Not a continuity-chat concern. |
| Causal reasoning | Out of normal chat path | Separate vertical. Separate endpoint. |
| Email context + email friction enrichment | Out of normal chat path | Integration feature. Not a continuity-chat concern. |
| Scheduling context | Out of normal chat path (router-gated) | Separate vertical. Separate endpoint. |
| Agent task context | Out of normal chat path (router-gated) | Separate product mode. |
| BM25 hybrid recall | Default-off; escape hatch only | Adds 4 DB queries + overhead. Not needed for continuity-first chat. |
| LLM summarisation inside `build_recall_context` | Removed | Hidden second LLM call. Not needed. |
| `st_block` from `personal_model.short_term.texts` | Removed from prompt | Duplicate of verbatim turn history. Weaker signal (assistant-only). |

---

## Memory Architecture

```
What we just talked about   →  Layer 4: last 8 verbatim turns (immediate context)
What happened before that   →  Layer 3: compressed session summary (older context)
What they've written on     →  Layer 1: continuity pack evidence (longitudinal, journal-derived)
  this topic over time
Everything else in memory   →  Layer 2: vector recall fallback (no topic only)
  (facts, nodes, reflections)
```

These layers are complementary and non-overlapping. Each covers a distinct temporal and source scope.

---

## Key Constraints

- Continuity pack requires journal entries. A user who only chats and never writes journal entries will not have a continuity pack.
- The 120-day compile window is the outer bound on how far back the continuity compiler looks. Evidence older than 120 days is not surfaced in normal chat.
- Global vector recall (`k=5`) is the fallback when no topic is detected. It searches journal embeddings, reflections, facts, and memory nodes.
- BM25 is preserved in the codebase as an escape hatch for explicit memory-retrieval queries but is not invoked on normal turns.
- Governance is a hard system layer — when present, it is never skipped.

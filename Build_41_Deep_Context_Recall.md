# Build 41 — Deep Context Recall
Goal: perfect long‑term conversational memory by stitching context, linking life events, and keeping persona‑stable recaps for the Companion Engine.

# Build 41 — Deep Context Recall
Goal: perfect long‑term conversational memory by stitching context, linking life events, and keeping persona‑stable recaps for the Companion Engine.

# Update: Narrative Engine (Build 42 precursor)
- Added schema `infra/sql/20251122_build42_narrative_engine.sql` for narrative stories, identity evolution events, and season-of-life labels.
- Worker persona update now runs `run_narrative_engine` to synthesize a short “Who you are becoming” narrative, success/struggle patterns, and season hints.
- New endpoint `/narrative/{person}/summary` returns latest narrative + season.
- Test script `scripts/narrative_engine_check.py` posts a turn, waits for workers, and fetches the narrative summary.

## What landed
- **Schema** (`infra/sql/20251122_build41_deep_context_recall.sql`)
  - `context_recalls`: stitched summaries per turn/thread with multi‑vector payloads, signals, and confidence.
  - `life_event_links`: links recall items to inferred life events/themes.
  - `thread_continuity_markers`: track long‑running threads with persona stability hints.
  - `context_compact_summaries`: compact summaries for fast LLM context injection.
  - Indexed on `person_id`, `created_at`, and thread for fast recall.
- **Pipelines & endpoints**
  - Worker memory ingest writes recalls, life‑event links, thread continuity markers, and compact summaries per turn (default `thread_id`=person_id).
  - Conversation context now includes `deep_recall` (recalls + events + threads) for downstream LLM usage.
  - Debug endpoint `/debug/deep_recall` exposes the stored recalls (for any person_id).
- **Test script**
  - `scripts/deep_context_recall_check.py` sends a turn, waits for workers, then fetches `/debug/deep_recall` to validate recalls/links/threads.
- **Signals wiring**
  - Worker payload now carries intents/topics/triage/emotion/plan facets into recalls; topic extraction falls back to a lightweight LLM, and we infer intent from the first detected intent or topic. Signals now include sentiment score + mood labels even with the lightweight sentiment heuristic.
  - Thread continuity defaults to person_id if no thread is provided; upsert keeps thread_id/signals fresh even on repeated content.
  - Recalls are compacted and vectorized; life‑event links are automatically attached (first entity/keyword).

## How to deploy
Run the migration in Supabase SQL editor or psql:
```sql
-- Build 41 Deep Context Recall
\ir infra/sql/20251122_build41_deep_context_recall.sql
```

## Current behavior
- Each turn produces a recall row (stitched summary + compact + vectors + signals), a life‑event link, a continuity marker (per thread/person), and a compact summary.
- Conversation context and `/debug/deep_recall` now surface these recalls for fast inspection and LLM grounding.

## Improve signals (why it helps)
- Signals carry `intent/topics/mood/tags` so the LLM can ground responses in user intent and themes without re‑deriving them each turn.
- We now auto-populate from turn pipeline (intents + topic manager fallback). Richer signals reduce prompt tokens and tighten relevance; if you add a stronger intent/topic detector, recalls will carry even more precise grounding.

## Notes
- Keep payloads small: store both rich `compact` JSON and a pre‑tokenized `tokens_est` for budget checks.
- Thread continuity should be updated on every turn to avoid jumping persona modes across long conversations.

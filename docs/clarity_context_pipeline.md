# Clarity Context Pipeline (Sakhi)

**Purpose:** Turn every message into persistent, explainable context so Sakhi plans with the person’s goals, guardrails, energy, time, and (eventually) finances in mind.

---

## 1) Capture (per message)
- **Write:** `episodes(person_id, ts, text, tags[], mood_score, source_ref)`
- **Emit event:** `memory.observed { person_id, episode_id }`

> Source of truth for the raw stream of life.

---

## 2) Enrich (worker, near-real-time)
Handlers consume `memory.observed` and write *idempotent* updates:

- **`tags_enricher`** → updates `episodes.tags`
- **`intent_goal_enricher`** → creates `goals(status='proposed')` on “I want to …”
- **`values_guardrail_enricher`** → upserts `preferences(scope='values', key='...')`
- **`aspect_writers`** → upserts `aspect_features`:
  - `time.time_slack`, `energy.energy_slack`, `finance.money_feasibility`, `values.values_alignment`
- **`short_horizon_aggregator`** → writes `short_horizon` (7d counts, tags, avg mood)

> Deterministic rules first; LLM inference later behind a feature flag.

---

## 3) Consolidate (nightly)
- **Themes** from tags (≥3 in 30d) → `themes`
- **Goal promotions** (repeated mentions) → `goals.status = 'active'`

> Mimics sleep-like consolidation; long-term structure emerges without scans.

---

## 4) Read models (single source of truth)
- **`person_summary_v`**: goals, values_prefs, themes, avg_mood_7d, aspect_snapshot
- **`short_horizon_v`**: 7-day rolling “what’s active now”

> UI and planner read the **same** views.

---

## 5) Context injection (every plan/evaluate call)
`base_context()` stitches:

```json
{
  "support": {
    "goals": [...],
    "values_prefs": [...],
    "themes": [...],
    "avg_mood_7d": 0.73,
    "aspects": [{"aspect":"time","key":"time.time_slack","value":{"score":0.65}} ...]
  },
  "short_horizon": { "recent_tags":[...], "avg_mood_7d": 0.73 },
  "input_text": "...", "intent_need": "plan", "horizon": "week"
}
```

---

## Ops Runbook Notes (new events & schedules)

- **Events emitted**
  - `observations.extracted` — payload includes LLM/fallback counts, average confidence.
  - `state_vector.updated` — carries readiness vector confidence and method (`llm` vs `heuristic`).
  - `conversation_suggestions` table (insert) — each delivered phrase is stored with style, confidence, policy meta for auditing.

- **Nightly consolidation**
  - Run `make consolidator` locally or hit `POST /worker/consolidate/run` with header `X-Worker-Token: <WORKER_CONTROL_TOKEN>`.
  - In Supabase, schedule with `pg_cron`/`pg_net`:
    ```sql
    select cron.schedule(
      'nightly_person_consolidation',
      '0 3 * * *',
      $$
        select net.http_post(
          url     := 'https://your-api-host/worker/consolidate/run',
          headers := jsonb_build_object('X-Worker-Token', 'shared-secret')
        );
      $$
    );
    ```

- **Prompt & policy updates**
  - Prompts live in `config/prompts/*.json`, policies in `config/policy/*.yml`.
  - Dev hot-reload is enabled by default (`SAKHI_CONFIG_HOT=1`). In production set `SAKHI_CONFIG_HOT=0` for stability.
  - To test new prompts, run `poetry run pytest sakhi/tests/api/test_llm_support.py::test_config_loader_hot_reload` and restart the API if hot reload is disabled.

--- 

# Sakhi Monorepo

## Key API Endpoints
- `POST /chat` – conversational interface (emotion-aware, multi-turn).
- `POST /journal/v2` – journaling pipeline (text + voice, intent tracking).
- `POST /plan` – drafts plans and schedules enrichment jobs.
- `POST /retrieval` – semantic recall over journal corpus.

## LLM Configuration
The runtime supports two providers:
1. **OpenAI** (direct): set `OPENAI_API_KEY` and optional overrides
   - `OPENAI_MODEL_CHAT` (default `gpt-4o-mini`)
   - `OPENAI_MODEL_EMBED` (default `text-embedding-3-small`)
   - `OPENAI_TIMEOUT` (seconds, default `30`)
2. **OpenRouter**: set `OPENROUTER_API_KEY` (optional `OPENROUTER_BASE_URL`, `OPENROUTER_TENANT`).

If both are present, requests prefer OpenAI, falling back to OpenRouter, with the stub provider as a final fallback.

Set `MODEL_CHAT`, `MODEL_TOOL`, or `MODEL_EMBED` if you need to override defaults for the router.

## Logging
Logging is JSON by default at DEBUG level in local/test (controlled by `SAKHI_LOG_LEVEL`).
Set `SAKHI_LOG_COLOR=0` to disable ANSI colors. Key events (classifier/chat responses, embeddings) are logged with `event` fields for easy filtering.

## Background Schedulers
- Launch an RQ worker for the background queues:
  ```bash
  poetry run python -m sakhi.apps.worker.main
  ```
- In a separate shell, run the scheduler loop (use `--once` for a single pass):
  ```bash
  # faster cadence for local testing
  SCHED_REFLECTION_INTERVAL_SEC=180 \
  SCHED_PRESENCE_INTERVAL_SEC=300 \
  ENABLE_PRESENCE_JOBS=0 \
  poetry run python scripts/run_schedulers.py
  ```
- Defaults: reflections enqueue every 24h and presence every 6h. Override with `SCHED_REFLECTION_INTERVAL_SEC` / `SCHED_PRESENCE_INTERVAL_SEC`, or disable presence with `ENABLE_PRESENCE_JOBS=0`.

# @sakhi/runner

Event bridge that wires together the entire Sakhi conversation pipeline for local experimentation: facet extraction → context building → planning → learning → action routing → weekly insights.

```
pnpm --filter @sakhi/runner dev
```

This starts an HTTP server (default `http://localhost:4310/events/message-ingested`). POST a payload that matches the `Message` contract and the pipeline will run, logging each stage. Set `MEMORY_PG_URL` (or `DATABASE_URL`) to persist memories; provide `TASK_ENDPOINT_URL` (e.g., FastAPI `/actions/task`) to persist routed tasks; and set `OPENROUTER_API_KEY` to enable LLM-grade facet extraction plus DeepSeek-rendered replies. Trigger weekly summaries via `POST /insights/run` with `{ "user_id": "…", "week_start": "YYYY-MM-DD" }` to see synthesized highlights.

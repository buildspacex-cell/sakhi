# Build 81 — Forecast Engine v1

This build introduces a deterministic 24-hour micro-forecasting layer for emotion, clarity, behavior, and risk windows. Results are cached in `forecast_cache` and mirrored into `personal_model.forecast_state`, with an API for clients.

## What changed
- Migration `infra/sql/20251224_build81_forecast_cache.sql` adds `forecast_cache`, `personal_model.forecast_state`, and an index.
- Engine `sakhi/apps/engine/forecast/engine.py` computes emotion/clarity/behavior forecasts, risk windows, and a rule-based summary (non-LLM).
- Worker `sakhi/apps/worker/tasks/forecast.py` writes cache + personal_model; scheduler runs daily and interval-based (`FORECAST_HOUR`, `FORECAST_INTERVAL_HOURS`).
- API `/v1/forecast` returns the latest forecast (personal_model fallback to cache).
- Tests `tests/test_build81_forecast_engine.py` cover rule paths and API smoke.

## Data contract (`forecast_state`)
```json
{
  "emotion_forecast": { "calm": 0.0, "irritability": 0.0, "fatigue": 0.0, "motivation": 0.0, "focus": 0.0 },
  "clarity_forecast": { "clarity_score": 0.0, "confusion_score": 0.0 },
  "behavior_forecast": { "adherence": 0.0, "procrastination_window": "", "action_window": "" },
  "risk_windows": { "overwhelm": "", "low_energy": "", "confusion": "" },
  "summary_text": "stable day expected",
  "updated_at": "ISO8601"
}
```

## Triggers
- Daily at `FORECAST_HOUR` (default 7 UTC) and interval-based every `FORECAST_INTERVAL_HOURS` (default 3).
- Can also be invoked manually via `run_forecast`.

## Notes
- No ingestion or embedding changes.
- Logic is deterministic; no LLM calls.
- Personal_model sync performed in worker to keep reads fast.

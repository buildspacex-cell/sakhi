# Build 82 — Adaptive Tone Engine v1

Deterministic tone computation layered on persona, coherence, conflict, forecast, and emotion signals. Stores tone in `personal_model.tone_state`, exposes it via API, and injects it into turn responses before LLM generation.

## What changed
- Migration `infra/sql/20251230_build82_tone_state.sql` adds `personal_model.tone_state`.
- Engine `sakhi/apps/engine/tone/engine.py` (with `__init__.py`) computes base + modifiers → final tone; best-effort write to personal_model.
- Turn pipeline: computes tone_state, passes in metadata, exposes `tone_used`, and keeps it available for prompt conditioning.
- API: `/v1/forecast` unaffected; tone is accessed via turn response (no separate route required).
- Scheduler untouched (tone computed per turn).
- Tests `tests/test_build82_tone_engine.py` cover tone modifiers and turn integration (mocked).

## Data contract (`tone_state`)
```json
{
  "base": "warm",
  "modifiers": ["soft", "guiding"],
  "final": "warm + soft + guiding",
  "updated_at": "ISO8601"
}
```

## Notes
- No ingestion or embedding changes.
- Deterministic rules only; no LLM.
- Base tone uses persona.custom_tone when present, else defaults to warm.
- Modifiers driven by conflict pressure, coherence clarity, forecast emotion probabilities, and emotion mode.

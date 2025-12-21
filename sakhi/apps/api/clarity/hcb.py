from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.clarity.anchors import compute_anchors
from sakhi.apps.api.clarity.base import base_context
from sakhi.apps.api.clarity.phrasing import generate_phrase
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.core.trace_store import persist_trace
from sakhi.apps.api.services.consolidate import decay_themes
from sakhi.libs.embeddings import embed_text


async def build_context_pack(user_text: str, need: str, horizon: str, person_id: str) -> Dict[str, Any]:
    await decay_themes(person_id)

    ctx = await base_context(person_id, user_text, need, horizon)
    anchors = await compute_anchors(ctx)

    personal_model_row = await q(
        "SELECT short_term, long_term FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )

    def _ensure_dict(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {}
        return {}

    short_term_model = _ensure_dict(personal_model_row.get("short_term") if personal_model_row else {})
    long_term_model = _ensure_dict(personal_model_row.get("long_term") if personal_model_row else {})

    ctx["personal_model"] = {
        "short_term": short_term_model,
        "long_term": long_term_model,
    }

    theme_rows = await q(
        """
        SELECT theme,
               (metrics->>'salience')::numeric AS salience,
               (metrics->>'significance')::numeric AS significance,
               (metrics->>'mentions')::int AS mentions,
               (metrics->>'last_seen')::timestamptz AS last_seen
        FROM journal_themes
        WHERE user_id = $1
        ORDER BY significance DESC NULLS LAST, salience DESC NULLS LAST
        LIMIT 5
        """,
        person_id,
    )

    recent_entries = await q(
        """
        SELECT id, content, created_at
        FROM journal_entries
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 10
        """,
        person_id,
    )

    def _themes_summary(rows: List[Dict[str, Any]]) -> str:
        pieces = []
        for row in rows:
            sal = float(row.get("salience") or 0.0)
            sig = float(row.get("significance") or 0.0)
            pieces.append(f"{row['theme']} (sig {sig:.2f}, sal {sal:.2f})")
        return "; ".join(pieces[:5])

    def _recent_summary(rows: List[Dict[str, Any]]) -> str:
        lines = []
        for row in rows[:5]:
            text = (row.get("content") or "").strip()
            if text:
                lines.append(f"- {text[:160]}")
        return "\n".join(lines)

    themes_summary = _themes_summary(theme_rows)
    recent_notes = _recent_summary(recent_entries)
    primary_theme_key = theme_rows[0]["theme"] if theme_rows else None

    ctx["themes_summary"] = themes_summary
    ctx["recent_notes"] = recent_notes
    ctx["primary_theme"] = primary_theme_key

    recall_snippets: list[str] = []
    try:
        vector = await embed_text(user_text)
        rows = await q(
            """
            SELECT id, text
            FROM episodes
            WHERE person_id = $1
              AND ts > NOW() - INTERVAL '90 days'
            ORDER BY embed_vec <=> $2
            LIMIT 5
            """,
            person_id,
            vector,
        )
        recall_snippets = [r.get("text", "") for r in rows if (r.get("text") or "").strip()]
    except Exception:
        recall_snippets = []

    prompt = f"""
You are Sakhi — a personal intelligence companion.
Context:
- Goals: {ctx['support']['goals']}
- Values/Prefs: {ctx['support']['values_prefs']}
- Themes: {ctx['support']['themes']}
- AvgMood(7d): {ctx['support']['avg_mood_7d']}
- Aspects(time/energy/finance/values): {ctx['support']['aspects']}
- Short-horizon: {ctx['short_horizon']}
- Anchors: {anchors}
- Themes summary: {themes_summary}
- Recent notes:\n{recent_notes}
- Recall snippets: {recall_snippets}
- Personal model (short term): {json.dumps(short_term_model, ensure_ascii=False)}
- Personal model (long term): {json.dumps(long_term_model, ensure_ascii=False)}

User input: {ctx['input_text']} | Need: {ctx['intent_need']} | Horizon: {ctx['horizon']}

Return JSON:
{{
  "options": {{"title": "...","steps": ["..."], "why": "..."}},
  "notes": ["...", "..."],
  "clarifications": ["..."],
  "risk_flags": ["..."],
  "confidence": {anchors['overall_confidence']}
}}
    """.strip()

    llm_raw = await call_llm(prompt)
    try:
        llm = json.loads(llm_raw) if isinstance(llm_raw, str) else llm_raw
    except json.JSONDecodeError:
        llm = {"raw": llm_raw}

    phrase = await generate_phrase(person_id, ctx, llm)

    debug = {
        "stage": "clarity_context_pack",
        "ctx": ctx,
        "anchors": anchors,
        "model_out": llm,
        "phrase": phrase,
        "recall_snippets": recall_snippets,
        "themes": theme_rows,
        "person_id": person_id,
        "flow": "clarity",
        "personal_model": ctx["personal_model"],
    }
    await persist_trace(debug)

    return {
        "context": ctx,
        "anchors": anchors,
        "llm": llm,
        "phrase": phrase,
        "themes": theme_rows,
        "themes_summary": themes_summary,
        "primary_theme": primary_theme_key,
        "recent_notes": recent_notes,
        "recall_snippets": recall_snippets,
        "person_summary": {
            "goals": ctx["support"]["goals"],
            "values_prefs": ctx["support"]["values_prefs"],
            "themes": ctx["support"]["themes"],
            "avg_mood_7d": ctx["support"]["avg_mood_7d"],
            "aspect_snapshot": ctx["support"]["aspects"],
        },
    }

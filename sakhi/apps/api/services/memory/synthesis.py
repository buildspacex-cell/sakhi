from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence, Tuple

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch
from sakhi.libs.schemas.settings import get_settings

settings = get_settings()

HORIZON_WEEKLY = "weekly"
HORIZON_MONTHLY = "monthly"


def _coerce_record(row: Dict[str, Any]) -> Dict[str, Any]:
    payload = row.get("record") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    return {
        "id": row.get("id"),
        "text": (payload.get("text") or payload.get("summary") or payload.get("raw_text") or "").strip(),
        "tags": payload.get("tags") or payload.get("themes") or [],
        "mood": payload.get("mood") or payload.get("emotion"),
        "created_at": row.get("created_at"),
    }


def _tokenise(text: str) -> List[str]:
    tokens = []
    for raw in text.lower().split():
        cleaned = raw.strip(".,!?\"'()[]{}")
        if len(cleaned) < 4:
            continue
        tokens.append(cleaned)
    return tokens


def _analyse_memories(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"total": 0, "top_themes": [], "summary": {}, "highlights": "", "semantic_notes": {}}

    tags: List[str] = []
    moods: List[str] = []
    tokens: List[str] = []
    non_empty_texts: List[str] = []

    for record in records:
        tags.extend(str(tag).lower() for tag in record.get("tags") or [])
        mood = record.get("mood")
        if mood:
            moods.append(str(mood).lower())
        text = record.get("text") or ""
        if text:
            non_empty_texts.append(text)
            tokens.extend(_tokenise(text))

    theme_counter = Counter(tags + tokens)
    top_themes = [
        {"theme": name, "weight": round(count / max(1, len(records)), 2)}
        for name, count in theme_counter.most_common(4)
        if name
    ]
    dominant_mood = Counter(moods).most_common(1)[0][0] if moods else "neutral"
    highlight = f"{len(records)} notes • dominant mood {dominant_mood}"
    if top_themes:
        highlight += " • themes: " + ", ".join(theme["theme"] for theme in top_themes[:3])

    summary = {
        "body": "Energy trending calm" if "rest" in theme_counter else "Pacing fluctuates but manageable",
        "mind": "Focused on reflection and planning" if "plan" in theme_counter or "plan" in tags else "Processing daily signals",
        "emotion": f"Leaning {dominant_mood}",
        "goals": "Progress logged across routines" if "practice" in theme_counter else "Needs intentional goals review",
    }

    semantic_notes = {
        "recent_examples": non_empty_texts[-3:],
        "mood_samples": moods[-5:],
        "counts": {"with_text": len(non_empty_texts), "with_tags": len(tags)},
    }

    return {
        "total": len(records),
        "top_themes": top_themes,
        "summary": summary,
        "highlights": highlight,
        "semantic_notes": semantic_notes,
    }


async def _fetch_records(person_id: str, window_start: datetime) -> List[Dict[str, Any]]:
    short_term_rows = await dbfetch(
        """
        SELECT id, record, created_at
        FROM memory_short_term
        WHERE user_id = $1
          AND created_at >= $2
        ORDER BY created_at ASC
        """,
        person_id,
        window_start,
    )
    episodic_rows = await dbfetch(
        """
        SELECT id, record, created_at
        FROM memory_episodic
        WHERE user_id = $1
          AND created_at >= $2
        ORDER BY created_at ASC
        """,
        person_id,
        window_start,
    )
    combined = [_coerce_record(row) for row in short_term_rows] + [_coerce_record(row) for row in episodic_rows]
    combined.sort(key=lambda item: item.get("created_at") or datetime.now(timezone.utc))
    return combined


def _calculate_drift(previous: Sequence[Dict[str, Any]], current: Sequence[Dict[str, Any]]) -> float:
    prev_set = {item.get("theme") for item in previous if item.get("theme")}
    curr_set = {item.get("theme") for item in current if item.get("theme")}
    if not curr_set:
        return 0.0
    overlap = len(prev_set & curr_set) / max(1.0, len(curr_set))
    return round(max(0.0, 1.0 - overlap), 2)


async def _previous_themes(person_id: str, horizon: str) -> List[Dict[str, Any]]:
    if horizon == HORIZON_MONTHLY:
        rows = await dbfetch(
            """
            SELECT top_themes
            FROM memory_monthly_recaps
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
        )
    else:
        rows = await dbfetch(
            """
            SELECT top_themes
            FROM memory_weekly_summaries
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
        )
    if not rows:
        return []
    record = rows[0].get("top_themes") or []
    if isinstance(record, list):
        return record
    try:
        parsed = json.loads(record)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


async def _log_theme_drift(person_id: str, horizon: str, previous: List[Dict[str, Any]], current: List[Dict[str, Any]], drift_score: float) -> None:
    if not settings.enable_weekly_synthesis_writes:
        logger.info("Weekly synthesis writes disabled; skipping theme drift logging")
        return
    if drift_score < 0.4:
        return
    prev_theme = previous[0]["theme"] if previous else None
    curr_theme = current[0]["theme"] if current else None
    if prev_theme == curr_theme:
        return
    await dbexec(
        """
        INSERT INTO memory_theme_drift_events (person_id, horizon, from_theme, to_theme, drift_score, evidence)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        """,
        person_id,
        horizon,
        prev_theme,
        curr_theme,
        drift_score,
        json.dumps({"previous": previous, "current": current}, ensure_ascii=False),
    )


async def _record_strength_events(person_id: str, metrics: Dict[str, Any]) -> None:
    if not settings.enable_weekly_synthesis_writes:
        logger.info("Weekly synthesis writes disabled; skipping strength events")
        return
    top_themes = metrics.get("top_themes") or []
    if not top_themes:
        await dbexec(
            """
            INSERT INTO memory_strength_events (person_id, event_kind, target, weight, payload)
            VALUES ($1, 'forget', 'themes', 0.25, $2::jsonb)
            """,
            person_id,
            json.dumps({"reason": "no themes detected"}, ensure_ascii=False),
        )
        return
    dominant = top_themes[0]["theme"]
    await dbexec(
        """
        INSERT INTO memory_strength_events (person_id, event_kind, target, weight, payload)
        VALUES ($1, 'strengthen', $2, 0.8, $3::jsonb)
        """,
        person_id,
        dominant,
        json.dumps({"top_themes": top_themes}, ensure_ascii=False),
    )


async def _compress_episodic(person_id: str, records: List[Dict[str, Any]]) -> None:
    if not settings.enable_weekly_synthesis_writes:
        logger.info("Weekly synthesis writes disabled; skipping semantic compression")
        return
    for record in records:
        source_id = record.get("id")
        if not source_id:
            continue
        summary_text = (record.get("text") or "")[:220]
        if not summary_text:
            continue
        await dbexec(
            """
            INSERT INTO memory_semantic_rollups (person_id, source_id, source_kind, semantic_summary, strength, payload)
            VALUES ($1, $2::uuid, 'memory', $3, 0.6, $4::jsonb)
            ON CONFLICT (person_id, source_id, source_kind)
            DO UPDATE SET semantic_summary = EXCLUDED.semantic_summary,
                          strength = EXCLUDED.strength,
                          payload = EXCLUDED.payload,
                          created_at = NOW()
            """,
            person_id,
            source_id,
            summary_text,
            json.dumps({"tags": record.get("tags") or []}, ensure_ascii=False),
        )


async def _update_personal_model(person_id: str, horizon: str, metrics: Dict[str, Any]) -> None:
    if not settings.enable_weekly_synthesis_personal_model_writes:
        logger.info("Weekly synthesis \u2192 personal_model writes disabled")
        return
    layer_key = "weekly_memory" if horizon == HORIZON_WEEKLY else "monthly_memory"
    payload = {
        "summary": metrics.get("summary"),
        "highlights": metrics.get("highlights"),
        "themes": metrics.get("top_themes"),
        "drift_score": metrics.get("drift_score"),
        "updated_at": datetime.utcnow().isoformat(),
    }
    await dbexec(
        """
        UPDATE personal_model
        SET long_term = COALESCE(long_term, '{}'::jsonb) || jsonb_build_object($2::text, $3::jsonb),
            updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
        layer_key,
        json.dumps(payload, ensure_ascii=False),
    )


async def _upsert_weekly(person_id: str, window_start: date, window_end: date, metrics: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.enable_weekly_synthesis_writes:
        logger.info("Weekly synthesis writes disabled; skipping weekly upsert")
        return {
            "week_start": str(window_start),
            "week_end": str(window_end),
            "summary": {},
            "top_themes": [],
            "highlights": None,
            "drift_score": 0.0,
        }
    await dbexec(
        """
        INSERT INTO memory_weekly_summaries (person_id, week_start, week_end, summary, highlights, top_themes, drift_score, semantic_notes)
        VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7, $8::jsonb)
        ON CONFLICT (person_id, week_start)
        DO UPDATE SET
            week_end = EXCLUDED.week_end,
            summary = EXCLUDED.summary,
            highlights = EXCLUDED.highlights,
            top_themes = EXCLUDED.top_themes,
            drift_score = EXCLUDED.drift_score,
            semantic_notes = EXCLUDED.semantic_notes,
            created_at = NOW()
        """,
        person_id,
        window_start,
        window_end,
        json.dumps(metrics.get("summary") or {}, ensure_ascii=False),
        metrics.get("highlights"),
        json.dumps(metrics.get("top_themes") or [], ensure_ascii=False),
        metrics.get("drift_score") or 0.0,
        json.dumps(metrics.get("semantic_notes") or {}, ensure_ascii=False),
    )
    return {
        "week_start": str(window_start),
        "week_end": str(window_end),
        "summary": metrics.get("summary"),
        "top_themes": metrics.get("top_themes"),
        "highlights": metrics.get("highlights"),
        "drift_score": metrics.get("drift_score"),
    }


async def _upsert_monthly(person_id: str, scope_start: date, scope_end: date, metrics: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.enable_weekly_synthesis_writes:
        logger.info("Weekly synthesis writes disabled; skipping monthly upsert")
        return {
            "month_start": str(scope_start),
            "month_end": str(scope_end),
            "summary": {},
            "top_themes": [],
            "chapter_hint": None,
            "drift_score": 0.0,
        }
    await dbexec(
        """
        INSERT INTO memory_monthly_recaps (person_id, month_scope, summary, highlights, top_themes, chapter_hint, drift_score, compression)
        VALUES ($1, daterange($2, $3, '[]'), $4::jsonb, $5, $6::jsonb, $7, $8, $9::jsonb)
        ON CONFLICT (person_id, month_scope)
        DO UPDATE SET
            summary = EXCLUDED.summary,
            highlights = EXCLUDED.highlights,
            top_themes = EXCLUDED.top_themes,
            chapter_hint = EXCLUDED.chapter_hint,
            drift_score = EXCLUDED.drift_score,
            compression = EXCLUDED.compression,
            created_at = NOW()
        """,
        person_id,
        scope_start,
        scope_end,
        json.dumps(metrics.get("summary") or {}, ensure_ascii=False),
        metrics.get("highlights"),
        json.dumps(metrics.get("top_themes") or [], ensure_ascii=False),
        metrics.get("chapter_hint"),
        metrics.get("drift_score") or 0.0,
        json.dumps(metrics.get("semantic_notes") or {}, ensure_ascii=False),
    )
    return {
        "month_start": str(scope_start),
        "month_end": str(scope_end),
        "summary": metrics.get("summary"),
        "top_themes": metrics.get("top_themes"),
        "chapter_hint": metrics.get("chapter_hint"),
        "drift_score": metrics.get("drift_score"),
    }


async def _maybe_create_life_chapter(person_id: str, scope_start: date, scope_end: date, metrics: Dict[str, Any]) -> None:
    top_themes = metrics.get("top_themes") or []
    if not top_themes or (metrics.get("drift_score") or 0) < 0.6:
        return
    arc_name = f"{top_themes[0]['theme'].title()} Chapter"
    await dbexec(
        """
        INSERT INTO life_arcs (person_id, arc_name, start_scope, end_scope, summary, sentiment, tags, narrative)
        VALUES ($1, $2, $3, $4, $5, 0.55, $6::text[], $7::jsonb)
        ON CONFLICT DO NOTHING
        """,
        person_id,
        arc_name,
        datetime.combine(scope_start, datetime.min.time(), tzinfo=timezone.utc),
        datetime.combine(scope_end, datetime.min.time(), tzinfo=timezone.utc),
        metrics.get("highlights") or "Emerging chapter detected via memory synthesis.",
        [theme["theme"] for theme in top_themes],
        json.dumps({"source": "memory_synthesis"}, ensure_ascii=False),
    )


async def run_memory_synthesis(person_id: str, *, horizon: str = HORIZON_WEEKLY) -> Dict[str, Any]:
    normalized = HORIZON_MONTHLY if horizon.lower().startswith("month") else HORIZON_WEEKLY
    window_days = 30 if normalized == HORIZON_MONTHLY else 7
    now = datetime.now(timezone.utc)
    window_start_dt = now - timedelta(days=window_days)
    records = await _fetch_records(person_id, window_start_dt)
    if not records:
        return {"status": "no_data", "person_id": person_id, "horizon": normalized}

    metrics = _analyse_memories(records)
    previous = await _previous_themes(person_id, normalized)
    drift_score = _calculate_drift(previous, metrics.get("top_themes") or [])
    metrics["drift_score"] = drift_score
    metrics["chapter_hint"] = (
        f"Life chapter shift toward {metrics['top_themes'][0]['theme']}"
        if normalized == HORIZON_MONTHLY and metrics.get("top_themes")
        else None
    )

    await _compress_episodic(person_id, records)
    await _record_strength_events(person_id, metrics)
    await _log_theme_drift(person_id, normalized, previous, metrics.get("top_themes") or [], drift_score)

    if normalized == HORIZON_MONTHLY:
        scope_start = (now - timedelta(days=30)).date()
        scope_end = now.date()
        result = await _upsert_monthly(person_id, scope_start, scope_end, metrics)
        await _maybe_create_life_chapter(person_id, scope_start, scope_end, metrics)
    else:
        scope_end = now.date()
        scope_start = (now - timedelta(days=7)).date()
        result = await _upsert_weekly(person_id, scope_start, scope_end, metrics)

    await _update_personal_model(person_id, normalized, metrics)
    return {"status": "ok", "person_id": person_id, "horizon": normalized, "result": result}


async def fetch_weekly_summaries(person_id: str, limit: int = 4) -> Dict[str, Any]:
    rows = await dbfetch(
        """
        SELECT week_start, week_end, summary, highlights, top_themes, drift_score, semantic_notes, created_at
        FROM memory_weekly_summaries
        WHERE person_id = $1
        ORDER BY week_start DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )
    for row in rows:
        if row.get("drift_score") is not None:
            row["drift_score"] = float(row["drift_score"])
    return {"person_id": person_id, "items": rows}


async def fetch_monthly_recaps(person_id: str, limit: int = 3) -> Dict[str, Any]:
    rows = await dbfetch(
        """
        SELECT month_scope, summary, highlights, top_themes, chapter_hint, drift_score, compression, created_at
        FROM memory_monthly_recaps
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )
    def _format_range(value: Any) -> Dict[str, Any] | None:
        if value is None:
            return None
        lower = getattr(value, "lower", None)
        upper = getattr(value, "upper", None)
        bounds = getattr(value, "_bounds", None)
        return {
            "lower": lower.isoformat() if isinstance(lower, (datetime, date)) else lower,
            "upper": upper.isoformat() if isinstance(upper, (datetime, date)) else upper,
            "bounds": bounds,
            "text": str(value),
        }

    for row in rows:
        if row.get("drift_score") is not None:
            row["drift_score"] = float(row["drift_score"])
        row["month_scope"] = _format_range(row.get("month_scope"))
    return {"person_id": person_id, "items": rows}


__all__ = [
    "run_memory_synthesis",
    "fetch_weekly_summaries",
    "fetch_monthly_recaps",
]

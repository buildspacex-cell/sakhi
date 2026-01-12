from __future__ import annotations

"""
Soul conflict & soul friction are HIGH-STAKES signals.

Rules:
- NEVER infer from a single episode alone.
- NEVER populate unless confidence >= 0.6.
- EMPTY {} is a valid and preferred state.
- These fields represent longitudinal tension, not daily mood.
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.worker.jobs import _get_router
from sakhi.libs.embeddings import embed_text, to_pgvector
from sakhi.libs.schemas import get_settings

LOGGER = logging.getLogger(__name__)


def _log(prefix: str, msg: str, **kwargs: Any) -> None:
    if kwargs:
        LOGGER.info("[%s] %s %s", prefix, msg, kwargs)
    else:
        LOGGER.info("[%s] %s", prefix, msg)


def _parse_ts(ts_val: Any) -> datetime | None:
    if isinstance(ts_val, datetime):
        return ts_val.astimezone(timezone.utc)
    if isinstance(ts_val, str):
        try:
            dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


async def _fetch_journals(user_id: str, start: datetime, end: datetime) -> list[dict]:
    rows = await dbfetch(
        """
        SELECT id, content, ts
        FROM journal_entries
        WHERE user_id = $1
          AND ts >= $2
          AND ts < $3
        ORDER BY ts ASC
        """,
        user_id,
        start,
        end,
    )
    return [dict(row) for row in rows]


async def _summarize_day(journals: Sequence[Dict[str, Any]], window_start: datetime) -> str:
    # Concatenate journal texts in chronological order
    corpus_parts: List[str] = []
    for j in journals:
        text = (j.get("content") or "").strip()
        if text:
            corpus_parts.append(text)
    corpus = "\n\n".join(corpus_parts).strip()
    fallback = f"Episodic summary (v2.1 stub) for {window_start.date()}"
    if not corpus:
        return fallback

    system_msg = (
        "Summarize the day as a whole in 2-4 sentences using neutral, factual language. "
        "Do not give advice, interpretation, identity claims, or future predictions. "
        "Plain text only; no bullets, emojis, or headings."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": corpus},
    ]
    model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
    try:
        router = _get_router()
        resp = await router.chat(messages=messages, model=model)
        summary = (resp.text or "").strip()
        if summary:
            return summary
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"llm_summary_failed {exc}")
    return fallback


async def _embed_summary(text: str) -> tuple[Sequence[float], bool]:
    vector = await embed_text(text)
    if isinstance(vector, list) and vector and isinstance(vector[0], list):
        vector = vector[0]
    if not isinstance(vector, list):
        return [], False
    return vector, True


# context_tags are weak deterministic signals used by longitudinal learning
def extract_context_tags(text: str) -> List[Dict[str, str]]:
    if not isinstance(text, str) or not text.strip():
        return []
    lowered = text.lower()
    tags: List[Dict[str, str]] = []

    def add_tag(dimension: str, signal_key: str, polarity: str, intensity: str = "medium"):
        if len(tags) >= 5:
            return
        tags.append(
            {
                "dimension": dimension,
                "signal_key": signal_key,
                "polarity": polarity,
                "intensity": intensity,
            }
        )

    if any(k in lowered for k in ["sleep", "rested", "fatigue", "tired", "exhausted"]):
        add_tag("body", "energy_rest", "neutral")
    if any(k in lowered for k in ["back pain", "stiff neck", "ache", "sore"]):
        add_tag("body", "discomfort", "up")
    if any(k in lowered for k in ["stress", "anxiety", "overwhelm"]):
        add_tag("emotion", "stress", "up")
    if any(k in lowered for k in ["calm", "relief", "grounded"]):
        add_tag("emotion", "calm", "down")
    if any(k in lowered for k in ["energized", "productive", "focus"]):
        add_tag("energy", "activation", "up")
    if any(k in lowered for k in ["sluggish", "drained", "tired"]):
        add_tag("energy", "activation", "down")
    if any(k in lowered for k in ["meeting", "deadline", "calls", "workload"]):
        add_tag("work", "load", "up")
    if any(k in lowered for k in ["break", "walk", "rest"]):
        add_tag("work", "recovery", "down")
    if any(k in lowered for k in ["clarity", "plan", "organized"]):
        add_tag("mind", "clarity", "up")
    if any(k in lowered for k in ["scattered", "distracted", "fragmented"]):
        add_tag("mind", "clarity", "down")

    return tags


async def extract_episodic_soul(summary_text: str) -> Dict[str, List[str]]:
    """
    Extract lightweight soul signals from an episodic summary.
    Must be neutral, non-interpretive, and grounded in the episode only.
    """
    prompt = f"""You are annotating a single day of lived experience.

From the text below, extract:

soul: core themes, values, or tensions present

soul_shadow: inner friction, avoidance, fear, or conflict present

soul_light: moments of alignment, clarity, relief, or growth present

Rules:

Use only what is evident in the text

Do NOT give advice, judgments, or identity claims

Do NOT infer future direction

Use short phrases only

If nothing is evident, return empty arrays

Return valid JSON only in this exact shape:

{{
"soul": [],
"soul_shadow": [],
"soul_light": []
}}

Text:
\"\"\"{summary_text}\"\"\""""

    model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
    try:
        router = _get_router()
        resp = await router.chat(messages=[{"role": "user", "content": prompt}], model=model)
        raw = (resp.text or "").strip()
        parsed: Dict[str, Any] = json.loads(raw)
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"soul_extraction_failed {exc}")
        return {"soul": [], "soul_shadow": [], "soul_light": []}

    def _listify(val: Any) -> List[str]:
        if isinstance(val, list):
            return [str(x) for x in val if isinstance(x, (str, int, float))]
        return []

    return {
        "soul": _listify(parsed.get("soul")),
        "soul_shadow": _listify(parsed.get("soul_shadow")),
        "soul_light": _listify(parsed.get("soul_light")),
    }


async def extract_soul_conflict(recent_episode_summaries: list[str]) -> Dict[str, Any]:
    """
    Derives soul_conflict ONLY if repeated tension is evident across multiple episodes.
    """
    if len(recent_episode_summaries) < 3:
        return {}

    prompt = """
You are detecting recurring INNER VALUE CONFLICTS across multiple days.

Rules:
- Only output conflict if it clearly repeats across days.
- Do NOT infer from stress, fatigue, or workload.
- If evidence is weak, output EMPTY JSON {}.
- Output STRICT JSON only.

Definition:
Soul conflict = value vs value tension (e.g. growth vs stability).

Schema:
{
  "themes": [
    {
      "left": string,
      "right": string,
      "strength": number (0-1),
      "confidence": number (0-1)
    }
  ]
}
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[
                {"role": "system", "content": "You extract conservative, evidence-based inner conflicts."},
                {"role": "user", "content": prompt + "\n\nEPISODES:\n" + "\n---\n".join(recent_episode_summaries)},
            ],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        themes = [t for t in parsed.get("themes", []) if t.get("confidence", 0) >= 0.6]
        return {"themes": themes} if themes else {}
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"soul_conflict_failed {exc}")
        return {}


async def extract_soul_friction(recent_episode_summaries: list[str]) -> Dict[str, Any]:
    """
    Derives soul_friction ONLY when direction is stable but action/resourcing is blocked.
    """
    if len(recent_episode_summaries) < 3:
        return {}

    prompt = """
You are detecting recurring MISALIGNMENT between inner direction
and lived reality across multiple days.

Rules:
- Only output friction if the same block repeats.
- Do NOT moralize or assign blame.
- If unclear, output EMPTY JSON {}.
- Output STRICT JSON only.

Definition:
Soul friction = value vs reality resistance.

Schema:
{
  "areas": [
    {
      "direction": string,
      "block": string,
      "intensity": number (0-1),
      "confidence": number (0-1)
    }
  ]
}
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[
                {"role": "system", "content": "You extract conservative resistance patterns."},
                {"role": "user", "content": prompt + "\n\nEPISODES:\n" + "\n---\n".join(recent_episode_summaries)},
            ],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        areas = [a for a in parsed.get("areas", []) if a.get("confidence", 0) >= 0.6]
        return {"areas": areas} if areas else {}
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"soul_friction_failed {exc}")
        return {}


async def _fetch_recent_episode_summaries(user_id: str, limit: int = 5) -> list[str]:
    rows = await dbfetch(
        """
        SELECT text
        FROM memory_episodic
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )
    summaries: list[str] = []
    for row in rows:
        text = (row.get("text") or "").strip()
        if text:
            summaries.append(text)
    return summaries


async def _fetch_recent_episode_summaries_before(user_id: str, limit: int, before_ts: datetime) -> list[str]:
    rows = await dbfetch(
        """
        SELECT text
        FROM memory_episodic
        WHERE user_id = $1
          AND created_at < $2
        ORDER BY created_at DESC
        LIMIT $3
        """,
        user_id,
        before_ts,
        limit,
    )
    summaries: list[str] = []
    for row in rows:
        text = (row.get("text") or "").strip()
        if text:
            summaries.append(text)
    return summaries


async def extract_emotion_loop(recent_summaries: list[str]) -> Dict[str, Any]:
    """
    Extract recurring emotional dynamics across episodes.
    Must be confidence-gated and safe.
    """
    if len(recent_summaries) < 3:
        return {}

    prompt = """
You are analyzing multiple daily summaries of a person.

Identify whether there is a recurring emotional loop across days.
An emotional loop is a repeated emotional pattern, not a mood.

Rules:
- Only output a loop if there is clear repetition across days.
- Do not give advice, diagnosis, or predictions.
- If confidence is low, return {}.

Return JSON only with:
{
  "loop_type": string,
  "pattern": [string],
  "confidence": float,
  "notes": string
}
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[
                {"role": "system", "content": "You extract recurring emotional dynamics conservatively."},
                {"role": "user", "content": prompt + "\n\nEPISODES:\n" + "\n---\n".join(recent_summaries)},
            ],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        confidence = float(parsed.get("confidence", 0.0))
        if confidence < 0.65:
            return {}
        return {
            "loop_type": parsed.get("loop_type"),
            "pattern": parsed.get("pattern") or [],
            "confidence": confidence,
            "notes": parsed.get("notes"),
        }
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"emotion_loop_failed {exc}")
        return {}


async def extract_episodic_emotional_state(summary_text: str) -> Dict[str, Any]:
    """
    Returns a coarse emotional aggregate for the day.
    Must be stable, non-reactive, and trend-oriented.
    """
    prompt = """
You are extracting a coarse emotional state for a single day based on a summary.

Rules:
- Output STRICT JSON only.
- Do NOT include advice, interpretation, identity, or future prediction.
- Use coarse, aggregated signals only.
- If unclear, return neutral defaults.

Schema:
{
  "tone": "positive|neutral|negative|mixed",
  "valence": number between -1.0 and 1.0,
  "activation": number between 0.0 and 1.0,
  "stability": number between 0.0 and 1.0
}

Defaults if unclear:
tone="neutral", valence=0.0, activation=0.5, stability=0.5
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[{"role": "system", "content": "You extract structured emotional signals."}, {"role": "user", "content": prompt + "\n\nSUMMARY:\n" + summary_text}],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        return {
            "tone": parsed.get("tone", "neutral"),
            "valence": float(parsed.get("valence", 0.0)),
            "activation": float(parsed.get("activation", 0.5)),
            "stability": float(parsed.get("stability", 0.5)),
        }
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"emotional_state_failed {exc}")
        return {
            "tone": "neutral",
            "valence": 0.0,
            "activation": 0.5,
            "stability": 0.5,
        }


async def extract_episodic_rhythm_state(summary_text: str) -> Dict[str, Any]:
    """
    Returns a macro rhythm assessment for the day.
    Focuses on sustainability, not momentary fatigue.
    """
    prompt = """
You are extracting a macro rhythm state for a single day.

Rules:
- Output STRICT JSON only.
- Do NOT include advice, interpretation, or future planning.
- Focus on trend-level rhythm signals only.
- If unclear, return neutral defaults.

Schema:
{
  "energy_trend": "up|down|flat",
  "load_balance": "underloaded|balanced|overextended",
  "recovery_signal": "adequate|insufficient|unknown"
}

Defaults if unclear:
energy_trend="flat", load_balance="balanced", recovery_signal="unknown"
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[{"role": "system", "content": "You extract rhythm sustainability signals."}, {"role": "user", "content": prompt + "\n\nSUMMARY:\n" + summary_text}],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        return {
            "energy_trend": parsed.get("energy_trend", "flat"),
            "load_balance": parsed.get("load_balance", "balanced"),
            "recovery_signal": parsed.get("recovery_signal", "unknown"),
        }
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"rhythm_state_failed {exc}")
        return {
            "energy_trend": "flat",
            "load_balance": "balanced",
            "recovery_signal": "unknown",
        }


async def run_episodic_consolidation_v21(person_id: str, payload: Dict[str, Any]) -> None:
    """
    Episodic v2.1 skeleton: compute daily window, read journals, log exit path.
    """
    user_id = payload.get("user_id") or payload.get("thread_id") or person_id
    entry_id = payload.get("entry_id")
    ts_raw = payload.get("ts")
    ts = _parse_ts(ts_raw)

    if not user_id:
        _log("episodic_v21", "missing user_id/thread_id; skipping", entry_id=entry_id, ts=ts_raw)
        return
    if ts is None:
        _log("episodic_v21", "invalid ts; skipping", user_id=user_id, entry_id=entry_id, ts=ts_raw)
        return

    # Compute calendar day window in UTC
    # Episodic windowing MUST use journal_entries.ts only.
    # Never use created_at / updated_at / STM timestamps for episodic logic.
    window_start = datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc)
    window_end = window_start + timedelta(days=1)
    _log(
        "episodic_v21",
        "window",
        user_id=user_id,
        entry_id=entry_id,
        start=window_start.isoformat(),
        end=window_end.isoformat(),
    )

    journals = await _fetch_journals(user_id, window_start, window_end)
    count = len(journals)
    _log(
        "episodic_v21",
        "found journals",
        user_id=user_id,
        entry_id=entry_id,
        start=window_start.isoformat(),
        end=window_end.isoformat(),
        journal_count=count,
    )

    if count == 0:
        _log(
            "episodic_v21",
            "exit: no journals in window",
            user_id=user_id,
            entry_id=entry_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
        )
        return
    if count == 1:
        _log(
            "episodic_v21",
            "exit: waiting for more journals",
            user_id=user_id,
            entry_id=entry_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
        )
        return

    # Eligible for consolidation: compute source ids and dedup hash
    source_entry_ids = sorted([str(j["id"]) for j in journals])
    joined = "|".join(source_entry_ids)
    content_hash = hashlib.md5(joined.encode("utf-8"), usedforsecurity=False).hexdigest()
    _log(
        "episodic_v21",
        "eligible for consolidation",
        user_id=user_id,
        entry_id=entry_id,
        start=window_start.isoformat(),
        end=window_end.isoformat(),
        journal_count=count,
        source_entry_ids=source_entry_ids,
        content_hash=content_hash,
    )

    dedup_row = await dbfetch(
        """
        SELECT id
        FROM memory_episodic
        WHERE user_id = $1
          AND record->>'episode_type' = 'daily'
          AND record->>'window_start' = $2
          AND record->>'window_end' = $3
        LIMIT 1
        """,
        user_id,
        window_start.isoformat(),
        window_end.isoformat(),
        one=True,
    )

    if dedup_row:
        _log(
            "episodic_v21",
            "exit: daily episode already exists for window",
            user_id=user_id,
            entry_id=entry_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
            content_hash=content_hash,
            episode_id=dedup_row.get("id"),
        )
        return

    # Create stub episode (no embeddings, no LLM)
    summary_text = await _summarize_day(journals, window_start)
    vector_values, has_vec = await _embed_summary(summary_text)
    vector_literal = to_pgvector(vector_values, length=1536) if has_vec else None
    soul_signals = await extract_episodic_soul(summary_text)
    episodic_emotional_state = await extract_episodic_emotional_state(summary_text)
    episodic_rhythm_state = await extract_episodic_rhythm_state(summary_text)
    recent_summaries_prev = await _fetch_recent_episode_summaries_before(user_id, limit=7, before_ts=window_end)
    recent_summaries = [summary_text] + recent_summaries_prev
    soul_conflict = await extract_soul_conflict(recent_summaries)
    soul_friction = await extract_soul_friction(recent_summaries)
    emotion_loop = await extract_emotion_loop(recent_summaries)

    episode_id = str(uuid.uuid4())
    record_payload = {
        "source_entry_ids": source_entry_ids,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "model_version": "episodic_v2.1",
        "episode_type": "daily",
        "summary": summary_text,
    }
    try:
        await dbexec(
            """
            INSERT INTO memory_episodic (
                id,
                user_id,
                person_id,
                text,
                record,
                vector_vec,
                content_hash,
                context_tags,
                ts,
                created_at,
                soul,
                soul_shadow,
                soul_light,
                emotional_state,
                rhythm_state,
                soul_conflict,
                soul_friction,
                emotion_loop
            )
            VALUES (
                $1,
                $2,
                $3::uuid,
                $4,
                $5::jsonb,
                CASE
                    WHEN $6::text IS NULL THEN NULL::vector
                    ELSE ($6::text)::vector
                END,
                $7,
                $8::jsonb,
                $9,
                $10,
                $11::jsonb,
                $12::jsonb,
                $13::jsonb,
                $14::jsonb,
                $15::jsonb,
                $16::jsonb,
                $17::jsonb,
                $18::jsonb
            )
            """,
            episode_id,
            user_id,
            person_id,
            summary_text,
        json.dumps(record_payload, ensure_ascii=False),
        vector_literal,
        content_hash,
        json.dumps(extract_context_tags(summary_text)),
        window_start,
        window_start,
        json.dumps(soul_signals.get("soul") or []),
        json.dumps(soul_signals.get("soul_shadow") or []),
        json.dumps(soul_signals.get("soul_light") or []),
            json.dumps(episodic_emotional_state),
            json.dumps(episodic_rhythm_state),
            json.dumps(soul_conflict),
            json.dumps(soul_friction),
            json.dumps(emotion_loop),
        )
        _log(
            "episodic_v21",
            "created episode",
            user_id=user_id,
            entry_id=entry_id,
            episode_id=episode_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
            content_hash=content_hash,
            source_entry_ids=source_entry_ids,
            has_vector=has_vec,
            summary_len=len(summary_text),
        )
        _log(
            "episodic_v21",
            "soul_enriched",
            episode_id=episode_id,
            soul=len(soul_signals.get("soul") or []),
            shadow=len(soul_signals.get("soul_shadow") or []),
            light=len(soul_signals.get("soul_light") or []),
        )
        _log(
            "episodic_v21",
            "emotion_rhythm_enriched",
            episode_id=episode_id,
            has_emotion=bool(episodic_emotional_state),
            has_rhythm=bool(episodic_rhythm_state),
        )
        _log(
            "episodic_v22",
            "conflict_friction_enriched",
            episode_id=episode_id,
            has_conflict=bool(soul_conflict),
            has_friction=bool(soul_friction),
        )
        _log(
            "episodic_v23",
            "emotion_loop_enriched",
            episode_id=episode_id,
            has_loop=bool(emotion_loop),
            confidence=(emotion_loop or {}).get("confidence"),
        )
    except Exception as exc:  # pragma: no cover - defensive
        _log(
            "episodic_v21",
            f"error creating episode: {exc}",
            user_id=user_id,
            entry_id=entry_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
            content_hash=content_hash,
            source_entry_ids=source_entry_ids,
        )
    return None


__all__ = ["run_episodic_consolidation_v21"]

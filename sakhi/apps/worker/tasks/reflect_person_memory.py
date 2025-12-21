from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping

try:
    from supabase import create_client
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    create_client = None  # type: ignore[assignment]

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch
from sakhi.apps.worker.tasks.generate_clarity_actions import generate_clarity_actions
from sakhi.apps.worker.tasks.reflect_morning_presence import reflect_morning_presence
from sakhi.libs.embeddings import embed_text, to_pgvector

from sakhi.apps.worker.utils.reflection_horizon import infer_reflection_horizon
from sakhi.libs.schemas import get_settings

LOGGER = logging.getLogger(__name__)
_SUPABASE_CLIENT: Any | None = None

SUMMARY_SYSTEM_PROMPT = (
    "You are Sakhi, a calm clarity companion. Summarise the person's past week using "
    "their journal snippets. Respond with STRICT JSON matching:\n"
    "{"
    '"body": "how their body or energy has been", '
    '"mind": "their mental focus or clarity", '
    '"emotion": "dominant emotional weather", '
    '"goals": "progress or friction with goals", '
    '"patterns": "notable rhythms or shifts"'
    "}."
    "Keep each value under 3 sentences, grounded in the provided notes. "
    "If a category is unclear, return a short string explaining the gap."
)


def reflect_person_memory(person_id: str, *, days: int = 7) -> None:
    """Entry point for RQ workers – run the async reflection coroutine."""

    asyncio.run(_reflect_person_memory(person_id, days=days))


async def _reflect_person_memory(person_id: str, days: int) -> None:
    from sakhi.apps.worker import jobs as worker_jobs  # lazy import to avoid circular dependency

    window_start = datetime.now(timezone.utc) - timedelta(days=days)
    journal_rows = await dbfetch(
        """
        SELECT content
        FROM journal_entries
        WHERE user_id = $1
          AND created_at >= $2
        ORDER BY created_at DESC
        """,
        person_id,
        window_start,
    )

    excerpts = [
        (row.get("content") or "").strip()
        for row in journal_rows
        if isinstance(row, Mapping)
    ]
    excerpts = [text for text in excerpts if text]
    if not excerpts:
        LOGGER.info("reflect_person_memory.no_entries person_id=%s", person_id)
        return

    corpus = "\n".join(excerpts[:40])

    router = worker_jobs._get_router()
    settings = get_settings()
    model = getattr(settings, "model_reflect", None) or worker_jobs.MODEL_REFLECT
    LOGGER.info("[reflect_person_memory] using model=%s", model)
    summary = await _generate_summary(router, model, corpus)
    if not summary:
        LOGGER.info("reflect_person_memory.no_summary person_id=%s", person_id)
        return

    related_people = extract_people_entities(excerpts)
    if related_people:
        await update_people_roles(person_id, related_people)

    rhythm_state = await timeseries_signals(person_id)
    if rhythm_state.get("energy") == "low":
        await delay_future_reflections(person_id, hours=6)

    await dbexec(
        """
        UPDATE personal_model
        SET long_term = COALESCE(long_term, '{}'::jsonb) || $2::jsonb,
            updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
        json.dumps(summary, ensure_ascii=False),
    )
    await reflect_morning_presence(person_id)
    from sakhi.apps.api.services.soul.engine import run_soul_engine

    await run_soul_engine(person_id)

    for label, value in summary.items():
        text_value = _coerce_text(value)
        if not text_value:
            continue

        vector = await _embed_text(text_value)
        if vector is None:
            continue

        # --- build proper Postgres vector literal ------------------------
        # Router occasionally returns incorrect (length 3) vectors if model fails.
        if not isinstance(vector, list):
            LOGGER.error("[reflect_memory] invalid embedding type: %s", type(vector))
            continue

        if len(vector) != 1536:
            LOGGER.error(
                "[reflect_memory] bad embedding length person_id=%s label=%s got=%s expected=1536",
                person_id,
                label,
                len(vector),
            )
            # skip writing a broken vector
            continue

        # safe vector literal for pgvector
        vector_literal = to_pgvector(vector)
        # -----------------------------------------------------------------
        await dbexec(
            """
            INSERT INTO personal_embeddings (person_id, label, content, embedding)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (person_id, label)
            DO UPDATE SET content = EXCLUDED.content,
                          embedding = EXCLUDED.embedding
            """,
            person_id,
            label,
            text_value,
            vector_literal,
        )

    LOGGER.info(
        "reflect_person_memory.completed person_id=%s slices=%s",
        person_id,
        len(summary),
    )
    await generate_clarity_actions(person_id, json.dumps(summary, ensure_ascii=False))


async def reflect_person_memory_delta(person_id: str, entry_text: str) -> Dict[str, Any]:
    """
    Lightweight async reflection – triggered right after journaling.
    Updates themes, theme_links, and writes preliminary insight to queue.
    """
    try:
        from sakhi.apps.worker.utils.llm import llm_reflect
    except ImportError:  # pragma: no cover - optional util module
        try:
            from apps.worker.utils.llm import llm_reflect  # type: ignore
        except ImportError as exc:  # pragma: no cover - defensive fallback
            LOGGER.warning("llm_reflect import failed: %s", exc)

            async def llm_reflect(text: str, *, mode: str = "delta_reflection") -> str:  # type: ignore
                return text

    horizon = infer_reflection_horizon(person_id, entry_text)
    themes = await classify_themes(entry_text)
    if len(themes) > 1:
        await update_theme_links(person_id, themes)

    insight_text = await llm_reflect(entry_text, mode="delta_reflection")
    captured_at = datetime.datetime.utcnow()
    deliver_after = captured_at + datetime.timedelta(minutes=horizon["delay"])
    record = {
        "person_id": person_id,
        "insight": {"text": insight_text, "themes": themes},
        "priority": "high" if horizon["urgency"] == "immediate" else "medium",
        "timing_hint": "soon" if horizon["urgency"] == "immediate" else "next_check_in",
        "delay_minutes": horizon["delay"],
        "deliver_after": deliver_after.isoformat(),
        "captured_at": captured_at.isoformat(),
    }
    await db_insert("insights_queue", record)
    return record


async def _generate_summary(router, model: str, corpus: str) -> Dict[str, str]:
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Recent journal excerpts:\n{corpus}"},
    ]
    try:
        response = await router.chat(messages=messages, model=model)
    except Exception as exc:  # pragma: no cover - defensive path
        LOGGER.warning("reflect_person_memory.chat_failed error=%s", exc)
        return _fallback_summary(corpus)

    payload = (response.text or "").strip()
    summary = _parse_summary(payload)
    if summary:
        return summary

    LOGGER.info("reflect_person_memory.parse_failed preview=%s", payload[:160])
    return _fallback_summary(corpus)


async def _embed_text(text: str) -> List[float] | None:
    try:
        vector = await embed_text(text)
    except Exception as exc:  # pragma: no cover - defensive path
        LOGGER.warning("reflect_person_memory.embed_failed error=%s", exc)
        return None

    if isinstance(vector, list) and vector and isinstance(vector[0], (int, float)):
        return [float(x) for x in vector]

    if isinstance(vector, list) and vector and isinstance(vector[0], list):
        inner = vector[0]
        try:
            return [float(x) for x in inner]
        except Exception:
            return None

    return None


def _parse_summary(payload: str) -> Dict[str, str] | None:
    if not payload:
        return None

    candidates = [payload, _strip_code_fences(payload)]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return {
                key: _coerce_text(value)
                for key, value in parsed.items()
                if key in {"body", "mind", "emotion", "goals", "patterns"}
            }
    return None


def _strip_code_fences(payload: str) -> str:
    stripped = payload.strip()
    if stripped.startswith("```"):
        stripped = stripped.lstrip("`")
        newline = stripped.find("\n")
        if newline != -1:
            stripped = stripped[newline + 1 :]
    if stripped.endswith("```"):
        stripped = stripped.rstrip("`").rstrip()
    return stripped


def _fallback_summary(corpus: str) -> Dict[str, str]:
    snippet = " ".join(corpus.split())
    if len(snippet) > 240:
        snippet = snippet[:240].rstrip() + "…"
    return {
        "body": "Energy signals unclear from recent notes.",
        "mind": "Mental focus details sparse; invite them to share more.",
        "emotion": "Emotional tone mixed or unreported.",
        "goals": "No explicit goals surfaced this week.",
        "patterns": snippet or "No salient patterns captured.",
    }


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


async def classify_themes(entry_text: str) -> List[str]:
    """Placeholder heuristic theme classifier."""
    if not entry_text:
        return ["general"]

    normalized = entry_text.lower()
    themes: List[str] = []
    theme_map = {
        "energy": ["tired", "energized", "sleep", "rest"],
        "work": ["work", "career", "office", "job"],
        "relationships": ["friend", "family", "partner", "relationship"],
        "wellness": ["exercise", "meditation", "health", "diet"],
        "creativity": ["art", "music", "writing", "project"],
    }

    for label, keywords in theme_map.items():
        if any(keyword in normalized for keyword in keywords):
            themes.append(label)

    if not themes:
        themes.append("general")
    return themes


async def update_theme_links(person_id: str, themes: List[str]) -> None:
    """Placeholder for theme co-occurrence tracking."""
    if not themes:
        return
    LOGGER.debug("update_theme_links placeholder person_id=%s themes=%s", person_id, themes)


def extract_people_entities(text_batch: Iterable[str]) -> List[str]:
    """Lightweight proper-noun extractor for people references."""
    candidates: set[str] = set()
    pattern = re.compile(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b")
    skip_terms = {"I", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
    for text in text_batch:
        if not text:
            continue
        for match in pattern.findall(text):
            cleaned = match.strip()
            if cleaned and cleaned not in skip_terms:
                candidates.add(cleaned)
    return sorted(candidates)[:5]


async def update_people_roles(person_id: str, people: List[str]) -> None:
    """Placeholder persistence for people-role associations."""
    if not people:
        return
    LOGGER.debug("update_people_roles placeholder person_id=%s people=%s", person_id, people)


async def timeseries_signals(person_id: str) -> Dict[str, Any]:
    """Placeholder rhythmic signal aggregator."""
    hour = datetime.utcnow().hour
    energy = "low" if hour < 7 or hour > 22 else "balanced"
    LOGGER.debug("timeseries_signals placeholder person_id=%s energy=%s", person_id, energy)
    return {"energy": energy}


async def delay_future_reflections(person_id: str, *, hours: int) -> None:
    """Placeholder delay mechanic for future reflections."""
    LOGGER.debug("delay_future_reflections placeholder person_id=%s hours=%s", person_id, hours)


def _get_supabase_client() -> Any | None:
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is None:
        if create_client is None:
            LOGGER.debug("Supabase client unavailable – library not installed.")
            _SUPABASE_CLIENT = False
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_API_KEY")
            if url and key:
                try:
                    _SUPABASE_CLIENT = create_client(url, key)
                except Exception as exc:  # pragma: no cover - optional client
                    LOGGER.warning("Supabase client init failed: %s", exc)
                    _SUPABASE_CLIENT = False
            else:
                _SUPABASE_CLIENT = False
    return _SUPABASE_CLIENT or None


async def db_insert(table: str, record: Dict[str, Any]) -> None:
    """Placeholder insert using Supabase if available, otherwise log."""
    client = _get_supabase_client()
    if client is None:
        LOGGER.debug("db_insert skipped table=%s record=%s", table, record)
        return

    loop = asyncio.get_running_loop()

    def _insert_sync() -> None:
        response = client.table(table).insert(record).execute()
        LOGGER.debug("Supabase insert response=%s", getattr(response, "data", response))

    try:
        await loop.run_in_executor(None, _insert_sync)
    except Exception as exc:  # pragma: no cover - external service failure
        LOGGER.warning("db_insert failed table=%s error=%s", table, exc)

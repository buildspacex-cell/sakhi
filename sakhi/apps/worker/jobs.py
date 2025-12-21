"""RQ job implementations for embeddings, salience, and reflections."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping

from sakhi.libs.embeddings import embed_text, to_pgvector
from sakhi.libs.ingest.emotion import detect_activation
from sakhi.libs.retrieval import build_reflection_context
from sakhi.libs.llm_router import (
    BaseProvider,
    LLMResponse,
    LLMRouter,
    OpenRouterProvider,
    Task,
)
from sakhi.libs.llm_router.openai_provider import make_openai_provider_from_env
from sakhi.libs.schemas import get_settings
from sakhi.libs.logging_utils import colorize
from sakhi.libs.schemas.db import get_async_pool
from sakhi.apps.worker.tasks.memory_synthesis import run_consolidate_person_models
from sakhi.apps.api.core.event_logger import log_event

LOGGER = logging.getLogger(__name__)
_ROUTER: LLMRouter | None = None
MODEL_TOOL = os.getenv("MODEL_TOOL") or os.getenv("MODEL_CHAT") or "deepseek/deepseek-chat"
MODEL_REFLECT = os.getenv("MODEL_REFLECT") or os.getenv("OPENAI_MODEL_CHAT") or os.getenv("MODEL_CHAT") or "gpt-4o-mini"
_CODE_FENCE_START_RE = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_CODE_FENCE_END_RE = re.compile(r"\s*```$", re.IGNORECASE)
JOURNAL_VECTOR_DIM = 1536


def _normalize_vector(vec: List[float] | None, *, length: int = JOURNAL_VECTOR_DIM) -> List[float]:
    floats = [float(x) for x in (vec or [])]
    if len(floats) >= length:
        return floats[:length]
    floats.extend([0.0] * (length - len(floats)))
    return floats


def _strip_code_fences(payload: str) -> str:
    stripped = payload.strip()
    stripped = _CODE_FENCE_START_RE.sub("", stripped)
    stripped = _CODE_FENCE_END_RE.sub("", stripped)
    return stripped.strip()


def _extract_json_candidate(payload: str) -> str | None:
    stripped = _strip_code_fences(payload)
    if not stripped:
        return None

    if stripped[0] in "{[" and stripped[-1] in "]}" and len(stripped) >= 2:
        return stripped

    brace_start = stripped.find("{")
    brace_end = stripped.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        return stripped[brace_start : brace_end + 1]

    bracket_start = stripped.find("[")
    bracket_end = stripped.rfind("]")
    if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
        return stripped[bracket_start : bracket_end + 1]

    return None


def _parse_json_payload(payload: str) -> Dict[str, Any] | None:
    candidate = payload.strip()
    if not candidate:
        return None

    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    extracted = _extract_json_candidate(candidate)
    if not extracted:
        return None

    try:
        parsed = json.loads(extracted)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _get_router() -> LLMRouter:
    global _ROUTER
    if _ROUTER is not None:
        return _ROUTER

    settings = get_settings()
    router = LLMRouter()
    chat_providers: List[str] = []

    provider_pref = (os.getenv("LLM_PROVIDER") or "openrouter").lower()

    openai_provider = make_openai_provider_from_env()
    if openai_provider and provider_pref in {"openai", "both"}:
        router.register_provider("openai", openai_provider)
        chat_providers.append("openai")

    api_key = settings.openrouter_api_key or os.getenv("LLM_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL")
    tenant = os.getenv("OPENROUTER_TENANT")

    if api_key and provider_pref in {"openrouter", "both"}:
        try:
            provider = OpenRouterProvider(api_key=api_key, base_url=base_url, tenant=tenant)
            router.register_provider("openrouter", provider)
            chat_providers.append("openrouter")
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to initialise OpenRouter provider: %s", exc)

    LOGGER.info(
        colorize("Worker router configured", "cyan"),
        extra={
            "event": "worker_router_config",
            "providers": list(router._providers.keys()),
            "chat_policy": router._config.policy.get(Task.CHAT),
            "model_chat": os.getenv("MODEL_CHAT"),
            "model_tool": os.getenv("MODEL_TOOL"),
            "openai_model_chat": os.getenv("OPENAI_MODEL_CHAT"),
        },
    )
    if not chat_providers:
        raise RuntimeError(
            "No chat providers configured. Set OPENAI_API_KEY or LLM_API_KEY/OPENROUTER credentials."
        )

    if provider_pref == "openai" and "openai" in chat_providers:
        chat_providers = [prov for prov in chat_providers if prov == "openai"] + [
            prov for prov in chat_providers if prov != "openai"
        ]
    elif provider_pref == "openrouter" and "openrouter" in chat_providers:
        chat_providers = [prov for prov in chat_providers if prov == "openrouter"] + [
            prov for prov in chat_providers if prov != "openrouter"
        ]

    router.set_policy(Task.CHAT, chat_providers)
    router.set_policy(Task.TOOL, chat_providers)
    _ROUTER = router
    return router


async def _fetch_entry(entry_id: str) -> tuple[str, datetime] | None:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            "SELECT content, created_at FROM journal_entries WHERE id = $1",
            entry_id,
        )
        if row is None:
            return None
        return row["content"] or "", row["created_at"]


async def _store_embedding(entry_id: str, embedding: List[float], model_name: str) -> None:
    pool = await get_async_pool()
    normalized = _normalize_vector(embedding)
    vector_literal = to_pgvector(normalized, length=JOURNAL_VECTOR_DIM)
    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO journal_embeddings (entry_id, model, embedding, embedding_vec, created_at)
            VALUES ($1, $2, $3::jsonb, $4::vector, now())
            ON CONFLICT (entry_id)
            DO UPDATE SET
                model = EXCLUDED.model,
                embedding = EXCLUDED.embedding,
                embedding_vec = EXCLUDED.embedding_vec,
                created_at = now()
            """,
            entry_id,
            model_name,
            json.dumps(normalized),
            vector_literal,
        )


async def _update_salience(entry_id: str, score: float) -> None:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO journal_inference (entry_id, container, payload, inference_type, source)
            VALUES ($1, 'cognition', jsonb_build_object('salience', to_jsonb($2::numeric)), 'structural', 'jobs._update_salience')
            """,
            entry_id,
            score,
        )


async def _write_reflection(user_id: str, kind: str, theme: str, text: str) -> None:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO reflections (user_id, kind, theme, content)
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            kind,
            theme,
            text,
        )


def _reflect_template(theme: str, mode: str = "daily") -> str:
    if mode == "weekly":
        return (
            "You are Sakhi. Synthesize a kind, pragmatic WEEKLY reflection.\n"
            "Return 6-10 bullets grouped by theme, then 'Next Week Focus' (3 items)."
        )
    return (
        "You are Sakhi. Synthesize a kind, pragmatic DAILY reflection.\n"
        "Return 5-8 bullets, then 'Next Steps' (3 items)."
    )


def _format_timestamp(value: Any) -> str:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # pragma: no cover - defensive
            return str(value)
    return str(value) if value is not None else "n/a"


def _trimmed(text: str, limit: int = 240) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def _format_reflection_context(context: Dict[str, Any]) -> str:
    theme = context.get("theme", "general")
    journals = context.get("journals") or []
    tasks = context.get("tasks") or []
    lines = [f"Theme: {theme}", ""]

    if journals:
        lines.append("Journal Highlights:")
        for journal in journals:
            created = _format_timestamp(journal.get("created_at"))
            title = journal.get("title") or "Untitled"
            content = _trimmed(journal.get("content") or "")
            salience = journal.get("salience")
            details = f"{created} :: {title}"
            if salience is not None:
                details += f" (salience={salience:.2f})"
            lines.append(f"- {details}\n  {content}")
    else:
        lines.append("Journal Highlights: none")

    lines.append("")
    if tasks:
        lines.append("Related Tasks:")
        for task in tasks:
            title = task.get("title") or "Untitled"
            status = task.get("status") or "unknown"
            due_at = task.get("due_at")
            due = _format_timestamp(due_at) if due_at else "unscheduled"
            description = _trimmed(task.get("description") or "", limit=160)
            lines.append(f"- [{status}] {title} (due {due})\n  {description}")
    else:
        lines.append("Related Tasks: none")

    lines.append("")
    counts = context.get("count") or {}
    lines.append(
        "Context Summary: "
        f"journals={counts.get('journals', len(journals))} "
        f"tasks={counts.get('tasks', len(tasks))} "
        f"window_start={_format_timestamp(context.get('window_start'))}"
    )
    return "\n".join(lines)


def _build_reflection_stub(kind: str, texts: List[str]) -> str:
    """Return a deterministic fallback summary when the LLM is unavailable."""

    window = "day" if kind == "daily" else "week"
    cleaned = [text.strip().splitlines()[0][:160] for text in texts if text.strip()]
    if not cleaned:
        return f"No entries recorded in the last {window}."

    bullets = [f"- {snippet}..." for snippet in cleaned[:5]]
    headline = "Highlights:" if kind == "daily" else "Weekly Highlights:"
    if kind == "daily":
        footer_title = "Next Steps:"
        footer_items = [
            "- Revisit tomorrow",
            "- Pick one meaningful action",
            "- Log a single win",
        ]
    else:
        footer_title = "Next Week Focus:"
        footer_items = [
            "- Celebrate one win",
            "- Note one challenge",
            "- Choose a focus area",
        ]

    return "\n".join([headline, *bullets, "", footer_title, *footer_items])


async def _request_reflection(
    kind: str,
    messages: List[Mapping[str, str]],
    *,
    model: str,
    fallback: str,
) -> str:
    try:
        router = _get_router()
        response = await router.chat(messages=messages, model=model)
        summary = (response.text or "").strip()
        if summary:
            return summary
    except Exception as exc:  # pragma: no cover - defensive path
        LOGGER.info("Reflection generation fell back to stub: %s", exc)
    return fallback


async def _create_embedding(entry_id: str) -> None:
    entry = await _fetch_entry(entry_id)
    if entry is None:
        LOGGER.warning("No journal entry found for embedding id=%s", entry_id)
        return

    content, _ = entry
    if not content:
        LOGGER.info("Journal entry id=%s has empty content; skipping embedding", entry_id)
        return

    settings = get_settings()
    model_name = getattr(settings, "model_embed", None) or os.getenv("MODEL_EMBED", "text-embedding-3-large")
    vector = await embed_text(content)
    if not vector:
        LOGGER.warning("Embedding pipeline returned empty vector for entry id=%s", entry_id)
        return

    await _store_embedding(entry_id, list(vector), model_name)
    LOGGER.info("Stored embedding for journal entry id=%s model=%s", entry_id, model_name)


async def _compute_salience(entry_id: str) -> None:
    entry = await _fetch_entry(entry_id)
    if entry is None:
        LOGGER.warning("No journal entry found for salience id=%s", entry_id)
        return

    content, created_at = entry
    length_score = min(len(content) / 500.0, 1.0)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_hours = max((datetime.now(timezone.utc) - created_at).total_seconds() / 3600.0, 0.0)
    recency_score = max(0.0, 1.0 - min(age_hours / 48.0, 1.0))
    salience = round(0.6 * length_score + 0.4 * recency_score, 4)

    await _update_salience(entry_id, salience)
    LOGGER.info("Updated salience for entry id=%s score=%.4f", entry_id, salience)


ENRICH_SYS = (
    "You are Sakhi’s journal enricher. Return STRICT JSON for fields: "
    "{track: one of [inner,outer], "
    "share_type: one of [thought,feeling,story,goal,question], "
    "actionability: number between 0 and 1, "
    "readiness: number between 0 and 1, "
    "timeline: {horizon: one of [none,today,week,month,quarter,year,long_term,custom_date], target_date?: string}, "
    "g_mvs: {target_horizon: bool, current_position: bool, constraints: bool, criteria: bool, assets_blockers: bool}, "
    "emotion: one of [calm,joy,hope,anger,sad,anxious,stressed], "
    "sentiment: number between -1 and 1, tags: [strings]}."
)


async def enrich_entry(entry_id: str) -> None:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            "SELECT content, facets FROM journal_entries WHERE id = $1",
            entry_id,
        )
    if row is None:
        LOGGER.warning("No journal entry found for enrichment id=%s", entry_id)
        return

    text = (row.get("content") or "").strip()
    hints = row.get("facets") or {}
    if isinstance(hints, (bytes, bytearray, memoryview)):
        try:
            hints = json.loads(bytes(hints).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            hints = {}
    elif isinstance(hints, str):
        try:
            hints = json.loads(hints)
        except json.JSONDecodeError:
            hints = {}
    elif not isinstance(hints, dict):
        hints = {}
    router = _get_router()
    settings = get_settings()
    model_name = (
        MODEL_TOOL
        or getattr(settings, "model_chat", None)
        or getattr(settings, "model_reflect", None)
        or "gpt-4o-mini"
    )
    messages = [
        {"role": "system", "content": ENRICH_SYS},
        {"role": "user", "content": f"Text:\n{text}\nJSON only."},
    ]

    raw_payload = ""
    payload: Dict[str, Any] | None = None
    try:
        response = await router.chat(messages=messages, model=model_name, force_json=True)
        raw_payload = (response.text or "").strip()
        LOGGER.info(
            colorize("LLM enrich response", "cyan"),
            extra={
                "event": "enrichment_llm_response",
                "entry_id": entry_id,
                "provider": response.provider,
                "model": response.model,
                "raw_text": raw_payload[:500],
            },
        )
        payload = _parse_json_payload(raw_payload)
    except Exception as exc:  # pragma: no cover - defensive fallback
        LOGGER.info("Enrichment fallback for entry id=%s: %s", entry_id, exc)
        payload = None

    if payload is None:
        if raw_payload:
            LOGGER.info(
                "Enrichment JSON parse failed for entry id=%s raw_preview=%s",
                entry_id,
                raw_payload[:500],
            )
        payload = {}

    def _bool(value: Any) -> bool:
        return bool(value) if value is not None else False

    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default

    defaults: Dict[str, Any] = {
        "track": payload.get("track") if payload.get("track") in {"inner", "outer"} else "inner",
        "share_type": payload.get("share_type")
        if payload.get("share_type") in {"thought", "feeling", "story", "goal", "question"}
        else "thought",
        "actionability": _float(payload.get("actionability"), 0.0),
        "readiness": _float(payload.get("readiness"), 0.0),
        "timeline": {
            "horizon": "none",
            "target_date": None,
        },
        "g_mvs": {
            "target_horizon": False,
            "current_position": False,
            "constraints": False,
            "criteria": False,
            "assets_blockers": False,
        },
        "emotion": payload.get("emotion")
        if payload.get("emotion") in {"calm", "joy", "hope", "anger", "sad", "anxious", "stressed"}
        else "calm",
        "sentiment": 0.0,
        "tags": [],
    }

    if isinstance(payload.get("timeline"), dict):
        timeline = payload["timeline"]
        horizon = timeline.get("horizon")
        if horizon in {"none", "today", "week", "month", "quarter", "year", "long_term", "custom_date"}:
            defaults["timeline"]["horizon"] = horizon
        target_date = timeline.get("target_date")
        if isinstance(target_date, str):
            defaults["timeline"]["target_date"] = target_date

    if isinstance(payload.get("g_mvs"), dict):
        g_mvs = payload["g_mvs"]
        for key in defaults["g_mvs"].keys():
            defaults["g_mvs"][key] = _bool(g_mvs.get(key))

    defaults["actionability"] = _float(payload.get("actionability"), defaults["actionability"])
    defaults["readiness"] = _float(payload.get("readiness"), defaults["readiness"])
    defaults["sentiment"] = max(-1.0, min(1.0, float(payload.get("sentiment", 0.0) or 0.0)))

    activation = detect_activation(text)
    sentiment_val = defaults["sentiment"]
    if activation >= 0.6 and sentiment_val >= 0:
        mood_label = "energized"
    elif sentiment_val > 0.3:
        mood_label = "positive"
    elif sentiment_val < -0.3:
        mood_label = "low"
    else:
        mood_label = "neutral"

    defaults["mood"] = mood_label
    defaults["activation"] = activation

    tags = payload.get("tags") or []
    if hints.get("tags"):
        hints_tags = hints.get("tags") or []
        if isinstance(hints_tags, (list, tuple)):
            tags = list(tags) + [tag for tag in hints_tags if isinstance(tag, str)]
    defaults["tags"] = sorted({tag for tag in tags if isinstance(tag, str)})

    if hints.get("mood") and defaults["emotion"] == "calm":
        defaults["emotion"] = hints.get("mood")

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO journal_inference (entry_id, container, payload, inference_type, source)
            VALUES ($1, 'context', $2::jsonb, 'interpretive', 'jobs._apply_defaults')
            """,
            entry_id,
            json.dumps(defaults),
        )


async def _salience_v2(entry_id: str) -> float:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            "SELECT length(coalesce(content, '')) AS length FROM journal_entries WHERE id = $1",
            entry_id,
        )
    length = int(row.get("length") or 0) if row else 0
    return min(1.0, math.log1p(max(length, 0)) / 8.0)


async def link_threads(entry_id: str, k: int = 3) -> None:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        entry_row = await connection.fetchrow(
            "SELECT user_id FROM journal_entries WHERE id = $1",
            entry_id,
        )
        if entry_row is None:
            return

        rows = await connection.fetch(
            """
            WITH ref AS (
                SELECT embedding
                FROM journal_embeddings
                WHERE entry_id = $1
            )
            SELECT je.id AS related_id,
                   1 - (emb.embedding <=> ref.embedding) AS similarity
            FROM journal_embeddings emb
            JOIN journal_entries je ON je.id = emb.entry_id
            CROSS JOIN ref
            WHERE je.user_id = $2 AND emb.entry_id <> $1
            ORDER BY emb.embedding <=> ref.embedding ASC
            LIMIT $3
            """,
            entry_id,
            entry_row["user_id"],
            k,
        )

        for row in rows:
            rel_id = row.get("related_id")
            similarity = float(row.get("similarity") or 0.0)
            await connection.execute(
                """
                INSERT INTO journal_links (src_id, dst_id, strength)
                VALUES ($1, $2, $3)
                ON CONFLICT (src_id, dst_id) DO NOTHING
                """,
                entry_id,
                rel_id,
                similarity,
            )


async def enqueue_embedding_and_salience(entry_id: str) -> None:
    """Run enrichment pipeline for a journal entry."""

    await _create_embedding(entry_id)
    await _compute_salience(entry_id)
    await enrich_entry(entry_id)
    await link_threads(entry_id)


def create_embedding(entry_id: str) -> None:
    """RQ job: create embeddings for a journal entry."""

    asyncio.run(_create_embedding(entry_id))


def update_salience(entry_id: str) -> None:
    """RQ job: update salience heuristics for a journal entry."""

    asyncio.run(_compute_salience(entry_id))


def run_daily_reflection(user_id: str, theme: str = "general") -> None:
    """Generate a daily reflection summary and persist it."""

    async def _run() -> None:
        await log_event(user_id, "reflection", "Daily reflection started", {"theme": theme})
        context = await build_reflection_context(user_id=user_id, theme=theme, limit=8)
        journals = context.get("journals") or []
        fallback = _build_reflection_stub("daily", [j.get("content") or "" for j in journals])

        messages: List[Mapping[str, str]] = [
            {"role": "system", "content": _reflect_template(theme, "daily")},
            {"role": "user", "content": _format_reflection_context(context)},
        ]

        settings = get_settings()
        model = getattr(settings, "model_reflect", None) or MODEL_REFLECT
        content = await _request_reflection("daily", messages, model=model, fallback=fallback)

        await _write_reflection(user_id, "daily", theme, content)
        await log_event(user_id, "reflection", "Daily reflection generated", {"theme": theme})

    asyncio.run(_run())


def run_weekly_summary(user_id: str, theme: str = "general") -> None:
    """Generate a weekly reflection summary and persist it."""

    async def _run() -> None:
        await log_event(user_id, "reflection", "Weekly reflection started", {"theme": theme})
        context = await build_reflection_context(user_id=user_id, theme=theme, limit=20)
        journals = context.get("journals") or []
        fallback = _build_reflection_stub("weekly", [j.get("content") or "" for j in journals])

        messages: List[Mapping[str, str]] = [
            {"role": "system", "content": _reflect_template(theme, "weekly")},
            {"role": "user", "content": _format_reflection_context(context)},
        ]

        settings = get_settings()
        model = getattr(settings, "model_reflect", None) or MODEL_REFLECT
        content = await _request_reflection("weekly", messages, model=model, fallback=fallback)

        await _write_reflection(user_id, "weekly", theme, content)
        await log_event(user_id, "reflection", "Weekly reflection generated", {"theme": theme})

    asyncio.run(_run())


def consolidate_person_models() -> None:
    """Consolidate short-term and long-term personal model layers."""

    run_consolidate_person_models()


def deliver_insight_to_presence_queue(row: Dict[str, Any]) -> None:
    """
    Push reflection insights into presence queue for delivery to user.
    """
    if not isinstance(row, dict):
        return
    try:
        delivered_flag = row.get("delivered", row.get("delivered_at"))
        if delivered_flag:
            return
        insight = row["insight"]
        message = {
            "person_id": row["person_id"],
            "text": insight["text"],
            "timing_hint": row.get("timing_hint", "next_check_in"),
        }
        enqueue_to_presence(message)
        mark_as_delivered(row["id"])
    except KeyError as exc:
        LOGGER.warning("deliver_insight_to_presence_queue missing key: %s", exc)


def enqueue_to_presence(message: Dict[str, Any]) -> None:
    """Placeholder hook for routing insights to the presence queue."""
    LOGGER.info("enqueue_to_presence message=%s", message)


def mark_as_delivered(row_id: Any) -> None:
    """Placeholder hook to persist delivery status."""
    LOGGER.info("mark_as_delivered row_id=%s", row_id)


__all__ = [
    "create_embedding",
    "enqueue_embedding_and_salience",
    "consolidate_person_models",
    "deliver_insight_to_presence_queue",
    "run_daily_reflection",
    "run_weekly_summary",
    "update_salience",
]

"""Persistence helpers for user memory capture."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sakhi.libs.llm_router import LLMRouter
from sakhi.libs.schemas.db import get_async_pool

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Represents a distilled insight about the user."""

    user_id: str
    kind: str
    summary: str
    importance: float = 0.0
    source_conversation: Optional[str] = None
    source_message_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "kind": self.kind,
            "summary": self.summary,
            "importance": float(self.importance),
            "source_conversation": self.source_conversation,
            "source_message_id": self.source_message_id,
            "metadata": self.metadata or {},
        }


class MemoryStore:
    """Storage abstraction for user_memories table."""

    @staticmethod
    async def upsert(entry: MemoryEntry) -> None:
        pool = await get_async_pool()
        payload = entry.as_dict()
        try:
            async with pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO user_memories (id, user_id, kind, summary, importance, source_conversation, source_message_id, metadata, created_at)
                    VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7::jsonb, now())
                    """,
                    payload["user_id"],
                    payload["kind"],
                    payload["summary"],
                    payload["importance"],
                    payload["source_conversation"],
                    payload["source_message_id"],
                    json.dumps(payload["metadata"], ensure_ascii=False),
                )
        except Exception as exc:  # pragma: no cover - tolerate absence during rollout
            logger.debug(
                "user_memories insert skipped: user_id=%s kind=%s error=%s",
                payload["user_id"],
                payload["kind"],
                exc,
            )

    @staticmethod
    async def fetch_recent(user_id: str, *, limit: int = 5) -> List[Dict[str, Any]]:
        if not user_id:
            return []
        pool = await get_async_pool()
        try:
            async with pool.acquire() as connection:
                rows = await connection.fetch(
                    """
                    SELECT id,
                           kind,
                           summary,
                           importance,
                           source_conversation,
                           source_message_id,
                           metadata,
                           created_at
                    FROM user_memories
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    max(1, min(limit, 50)),
                )
        except Exception as exc:  # pragma: no cover - tolerate absence during rollout
            logger.debug("user_memories fetch skipped: user_id=%s error=%s", user_id, exc)
            return []

        results: List[Dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload["id"] = str(payload.get("id"))
            payload["source_conversation"] = payload.get("source_conversation")
            payload["source_message_id"] = payload.get("source_message_id")
            payload["metadata"] = payload.get("metadata") or {}
            results.append(payload)
        return results


async def capture_salient_memory(
    *,
    router: Optional[LLMRouter],
    user_id: Optional[str],
    conversation_id: str,
    user_text: str,
    assistant_text: str,
    outer_features: Optional[Dict[str, Any]] = None,
    importance_threshold: float = 0.6,
) -> None:
    """Summarize the turn and persist it if considered salient."""

    if not user_id:
        return

    summary = None
    if router is not None:
        summary = await _summarize_with_llm(
            router=router,
            user_text=user_text,
            assistant_text=assistant_text,
            outer_features=outer_features,
        )
    if not summary:
        summary = _summarize_locally(user_text, assistant_text, outer_features)
    if not summary:
        return

    importance = _estimate_importance(outer_features)
    if importance < importance_threshold:
        return

    entry = MemoryEntry(
        user_id=user_id,
        kind="conversation_insight",
        summary=summary,
        importance=importance,
        source_conversation=conversation_id,
        metadata={
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "outer_features": outer_features or {},
        },
    )
    await MemoryStore.upsert(entry)


def _summarize_locally(user_text: str, assistant_text: str, features: Optional[Dict[str, Any]]) -> str:
    """Lightweight heuristic summary – can later be swapped for LLM surface realization."""

    pieces = []
    track = (features or {}).get("track")
    sentiment = (features or {}).get("sentiment")
    if track:
        pieces.append(f"track={track}")
    if sentiment is not None:
        pieces.append(f"sentiment={sentiment}")
    share = (features or {}).get("share_type")
    if share:
        pieces.append(f"share={share}")
    horizon = (features or {}).get("timeline", {}).get("horizon") if isinstance((features or {}).get("timeline"), dict) else None
    if horizon:
        pieces.append(f"horizon={horizon}")

    summary = f"User: {user_text.strip()[:240]}"
    if assistant_text:
        summary += f" | Assistant: {assistant_text.strip()[:160]}"
    if pieces:
        summary += f" ({', '.join(pieces)})"
    return summary


def _estimate_importance(features: Optional[Dict[str, Any]]) -> float:
    if not features:
        return 0.3
    actionability = float(features.get("actionability") or 0.2)
    readiness = float(features.get("readiness") or 0.2)
    sentiment = features.get("sentiment")
    sentiment_weight = 0.2
    if isinstance(sentiment, (int, float)):
        sentiment_weight = min(0.4, abs(float(sentiment)))
    return min(1.0, 0.4 * actionability + 0.3 * readiness + sentiment_weight + 0.1)


async def _summarize_with_llm(
    *,
    router: LLMRouter,
    user_text: str,
    assistant_text: str,
    outer_features: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Leverage the shared LLM router for higher-quality memory summaries."""

    try:
        model = os.getenv("MODEL_MEMORY") or os.getenv("MODEL_TOOL") or os.getenv("MODEL_CHAT", "gpt-4o-mini")
        system = (
            "You distill key personal insights from Sakhi conversations. "
            "Summaries should be factual, concise (<200 chars), and omit PII unless the user explicitly shared it."
        )
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"User said: {user_text.strip()}\n"
                    f"Sakhi replied: {assistant_text.strip()}\n"
                    f"Structured signals: {outer_features or {}}"
                ),
            },
        ]
        response = await router.chat(messages=messages, model=model)
        text = (response.text or "").strip()
        if not text:
            return None
        return text[:240]
    except Exception:
        return None


async def fetch_recent_memories(user_id: str, *, limit: int = 5) -> List[Dict[str, Any]]:
    """Convenience wrapper for MemoryStore.fetch_recent."""

    return await MemoryStore.fetch_recent(user_id, limit=limit)

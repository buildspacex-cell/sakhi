from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List

from sakhi.apps.api.core.db import exec as dbexec

LOGGER = logging.getLogger(__name__)


def _coerce_vector(candidate: Any) -> List[float]:
    try:
        return [float(x) for x in candidate][:1536]
    except Exception:
        return []


async def write_deep_context_recall(
    *,
    person_id: str,
    turn_id: str,
    thread_id: str | None,
    text: str,
    vector: List[float],
    sentiment: Dict[str, Any] | None = None,
    entities: List[str] | None = None,
    tags: List[str] | None = None,
    facets: Dict[str, Any] | None = None,
) -> None:
    """
    Persist a stitched context recall row (Build 41) plus lightweight linkages.
    Best-effort; failures are logged but do not raise.
    """

    stitched_summary = text[:800]
    compact = {
        "text": text[:640],
        "sentiment": sentiment or {},
        "entities": entities or [],
        "tags": tags or [],
        "facets": facets or {},
    }
    signals = {}
    if isinstance(sentiment, dict):
        signals["mood"] = sentiment.get("mood")
        signals["sentiment_score"] = sentiment.get("score")
    elif isinstance(sentiment, (int, float)):
        signals["sentiment_score"] = float(sentiment)
        if sentiment > 0.2:
            signals["mood"] = "positive"
        elif sentiment < -0.2:
            signals["mood"] = "negative"
        else:
            signals["mood"] = "neutral"
    if isinstance(facets, dict):
        intent_val = facets.get("intent") or (facets.get("intents")[0] if isinstance(facets.get("intents"), list) and facets.get("intents") else None)
        if intent_val:
            signals["intent"] = intent_val
        if facets.get("slots"):
            signals["slots"] = facets.get("slots")
        if facets.get("topics"):
            signals["topics"] = facets.get("topics")
    if tags:
        signals["tags"] = tags

    vectors = {"short_term": _coerce_vector(vector)}
    confidence = float(sentiment.get("score")) if isinstance(sentiment, dict) and sentiment.get("score") is not None else 0.0

    recall_id = uuid.uuid4()

    try:
        await dbexec(
            """
            INSERT INTO context_recalls (id, person_id, turn_id, thread_id, stitched_summary, compact, vectors, signals, confidence)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8::jsonb, $9)
            ON CONFLICT (person_id, turn_id)
            DO UPDATE SET
                thread_id = EXCLUDED.thread_id,
                stitched_summary = EXCLUDED.stitched_summary,
                compact = EXCLUDED.compact,
                vectors = EXCLUDED.vectors,
                signals = EXCLUDED.signals,
                confidence = EXCLUDED.confidence
            """,
            str(recall_id),
            person_id,
            turn_id,
            thread_id,
            stitched_summary,
            json.dumps(compact, ensure_ascii=False),
            json.dumps(vectors, ensure_ascii=False),
            json.dumps(signals, ensure_ascii=False),
            confidence,
        )
    except Exception as exc:  # pragma: no cover - best effort
        LOGGER.warning("[DeepRecall] failed to insert context_recalls for %s: %s", person_id, exc)
        return

    # Optional life-event link from first entity.
    if entities:
        try:
            await dbexec(
                """
                INSERT INTO life_event_links (id, person_id, recall_id, event_label, weight, evidence)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                str(uuid.uuid4()),
                person_id,
                str(recall_id),
                entities[0],
                1.0,
                json.dumps({"entities": entities[:3]}, ensure_ascii=False),
            )
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("[DeepRecall] failed to insert life_event_links for %s: %s", person_id, exc)

    # Thread continuity marker (upsert).
    if thread_id:
        try:
            await dbexec(
                """
                INSERT INTO thread_continuity_markers (id, person_id, thread_id, continuity_hint, persona_stability, last_turn_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, '{}'::jsonb, $5, NOW(), NOW())
                ON CONFLICT (person_id, thread_id)
                DO UPDATE SET continuity_hint = EXCLUDED.continuity_hint, last_turn_id = EXCLUDED.last_turn_id, updated_at = NOW()
                """,
                str(uuid.uuid4()),
                person_id,
                thread_id,
                text[:180],
                turn_id,
            )
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("[DeepRecall] failed to upsert thread_continuity for %s: %s", person_id, exc)

    # Compact summary for quick context injection.
    try:
        await dbexec(
            """
            INSERT INTO context_compact_summaries (id, person_id, recall_id, thread_id, compact, tokens_est)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            """,
            str(uuid.uuid4()),
            person_id,
            str(recall_id),
            thread_id,
            json.dumps(compact, ensure_ascii=False),
            len(text.split()),
        )
    except Exception as exc:  # pragma: no cover
        LOGGER.warning("[DeepRecall] failed to insert compact summary for %s: %s", person_id, exc)

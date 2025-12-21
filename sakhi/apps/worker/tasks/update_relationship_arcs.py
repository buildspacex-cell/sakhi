from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sakhi.apps.worker.utils.db import db_fetch, db_upsert
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.worker.utils.llm import extract_entities, sentiment_score


async def update_relationship_arcs(person_id: str, entry_text: str) -> None:
    """
    Updates relationship sentiment and strength per person_ref.
    """
    person_id = await resolve_person_id(person_id) or person_id
    people = extract_entities(entry_text)
    if not people:
        return

    for name in people:
        sentiment = sentiment_score(entry_text)
        arc: Dict[str, Any] = db_fetch(
            "relationship_arcs",
            {"person_id": person_id, "person_ref": name},
        )
        trend = dict(arc.get("sentiment_trend", {})) if arc else {}
        week_key = datetime.utcnow().strftime("w%U")
        trend[week_key] = sentiment
        strength = sum(trend.values()) / len(trend) if trend else 0.0
        record = {
            "person_id": person_id,
            "person_ref": name,
            "sentiment_trend": trend,
            "last_interaction_ts": datetime.utcnow().isoformat(),
            "strength_score": strength,
        }
        db_upsert("relationship_arcs", record)


__all__ = ["update_relationship_arcs"]

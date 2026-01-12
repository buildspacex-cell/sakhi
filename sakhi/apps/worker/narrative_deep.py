from __future__ import annotations

import logging
import json
from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.llm import call_llm
from sakhi.libs.embeddings import embed_text
from sakhi.libs.retrieval.episodic_retrieval import retrieve_episodic_slices

_DAYS_BACK = 1500  # TODO: tighten this window after lab debugging

PROMPT = """You are Sakhi's Soul Narrative engine.
Given compressed episodic memory, soul_state, and shadow/light patterns, return JSON with:
{
  "identity_arc": "...",
  "soul_archetype": "...",
  "life_phase": "...",
  "value_conflicts": [],
  "healing_direction": [],
  "narrative_tension": "low|medium|high"
}
Keep it concise and non-poetic.
Return valid JSON only, no prose."""


async def generate_deep_soul_narrative(person_id: str) -> Dict[str, Any]:
    logger = logging.getLogger(__name__)
    soul_row = await q("SELECT soul_state FROM personal_model WHERE person_id = $1", person_id, one=True)
    soul_state_raw = soul_row.get("soul_state") if soul_row else {}

    def _jsonish(val: Any) -> Any:
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return val or {}

    soul_state = _jsonish(soul_state_raw)

    narrative_query_text = (
        "long-term life themes, recurring inner conflicts, values, identity shifts, unresolved tensions, and patterns over time"
    )
    query_vector = await embed_text(narrative_query_text)
    logger.info(
        "[narrative_deep] retrieval start",
        extra={"person_id": person_id, "days_back": _DAYS_BACK},
    )
    retrieved = await retrieve_episodic_slices(user_id=person_id, query_vector=query_vector, k=7, days_back=_DAYS_BACK)

    episodic_payload: list[dict[str, Any]] = []
    rows = []
    if retrieved:
        episode_ids = [r["episode_id"] for r in retrieved]
        rows = await q(
            """
            SELECT
              id,
              soul,
              soul_shadow,
              soul_light,
              ts
            FROM memory_episodic
            WHERE id = ANY($1)
            ORDER BY ts ASC
            """,
            episode_ids,
        )
    else:
        logger.info("[narrative_deep] no episodic slices retrieved")
        try:
            stats = await q(
                f"""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE vector_vec IS NOT NULL) AS with_vec,
                       MIN(ts) AS min_ts,
                       MAX(ts) AS max_ts
                FROM memory_episodic
                WHERE user_id = $1 AND ts >= NOW() - INTERVAL '{_DAYS_BACK} days'
                """,
                person_id,
                one=True,
            )
            logger.info(
                "[narrative_deep] retrieval window stats",
                extra={"person_id": person_id, "stats": stats},
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("[narrative_deep] failed to fetch retrieval window stats: %s", exc)

    row_map = {str(r.get("id")): r for r in rows}
    for r in retrieved:
        row = row_map.get(r["episode_id"])
        if not row:
            continue
        ts_val = row.get("ts")
        if hasattr(ts_val, "isoformat"):
            ts_serialized = ts_val.isoformat()
        else:
            ts_serialized = ts_val

        episodic_payload.append(
            {
                "summary": r.get("summary") or "",
                "soul": _jsonish(row.get("soul")),
                "shadow": _jsonish(row.get("soul_shadow")),
                "light": _jsonish(row.get("soul_light")),
                "ts": ts_serialized,
            }
        )

    logger.info(
        "[narrative_deep] episodic grounding applied",
        extra={"episodes_used": len(episodic_payload), "episode_ids": [r["episode_id"] for r in retrieved]},
    )

    payload = {
        "soul_state": soul_state,
        "episodic": episodic_payload,
    }
    # Log inputs to the narrative worker so we can diagnose empty writes.
    def _preview(obj: Any, limit: int = 1200) -> str:
        try:
            text = json.dumps(obj, ensure_ascii=False)
        except Exception:
            text = str(obj)
        return text[:limit] + ("...<truncated>" if len(text) > limit else "")

    logger.info(
        "[narrative_deep] payload prepared",
        extra={
            "person_id": person_id,
            "soul_state_keys": list((soul_state or {}).keys()),
            "episodic_count": len(episodic_payload),
            "payload_preview": _preview(payload, limit=400),
        },
    )
    system_msg = {
        "role": "system",
        "content": (
            "You are Sakhi's Soul Narrative engine. Return ONLY a valid JSON object (no prose, no code fences). "
            "The JSON must contain keys: identity_arc, soul_archetype, life_phase, value_conflicts, "
            "healing_direction, narrative_tension. Use empty values if uncertain."
        ),
    }
    user_msg = {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)}
    messages = [system_msg, user_msg]
    logger.info(
        "[narrative_deep] llm request",
        extra={
            "person_id": person_id,
            "prompt_len": len(PROMPT),
            "messages_preview": _preview(messages, limit=800),
            "messages_full_preview": _preview(messages, limit=3000),
        },
    )
    raw_result = await call_llm(prompt=PROMPT, messages=messages, response_format={"type": "json_object"})

    parsed_result: Dict[str, Any] = {}
    raw_text: str = ""
    if isinstance(raw_result, dict):
        parsed_result = raw_result
    elif isinstance(raw_result, str):
        raw_text = raw_result
        try:
            parsed_result = json.loads(raw_result)
        except Exception:
            logger.warning(
                "[narrative_deep] llm parse failed; falling back to empty",
                extra={"person_id": person_id, "raw_len": len(raw_result)},
            )
            parsed_result = {}
    else:
        raw_text = str(raw_result)
        logger.warning(
            "[narrative_deep] unexpected llm result type; falling back to empty",
            extra={"person_id": person_id, "result_type": type(raw_result).__name__},
        )

    logger.info(
        "[narrative_deep] llm result received",
        extra={
            "person_id": person_id,
            "result_keys": list(parsed_result.keys()),
            "result_preview": _preview(parsed_result, limit=400),
            "raw_text_preview": _preview(raw_text or parsed_result, limit=400),
        },
    )

    try:
        await dbexec(
            "UPDATE personal_model SET soul_narrative = $2 WHERE person_id = $1",
            person_id,
            json.dumps(parsed_result, ensure_ascii=False),
        )
        logger.info(
            "[narrative_deep] db write success",
            extra={
                "person_id": person_id,
                "result_type": type(parsed_result).__name__,
            },
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "[narrative_deep] db write failed",
            extra={"person_id": person_id, "error": str(exc)},
        )
        raise
    return result

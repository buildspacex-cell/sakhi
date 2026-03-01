from __future__ import annotations

import json
import logging
from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.llm import call_llm

logger = logging.getLogger(__name__)


# Phase-1 Identity Momentum:
# - No replay debouncing
# - No episodic retrieval grounding
# - No caching
# These are intentional and deferred.


async def run_identity_momentum_deep(person_id: str) -> Dict[str, Any]:
    try:
        logger.info(
            "[identity_momentum] start",
            extra={"person_id": person_id},
        )

        pm_row = await q(
            "SELECT soul_state, emotion_state, rhythm_state FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        def _ensure_dict(val: Any) -> Dict[str, Any]:
            if isinstance(val, dict):
                return val
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    return {}
            return {}

        soul_state = _ensure_dict((pm_row or {}).get("soul_state"))
        emotion_state = _ensure_dict((pm_row or {}).get("emotion_state"))
        rhythm_state = _ensure_dict((pm_row or {}).get("rhythm_state"))

        logger.info(
            "[identity_momentum] loaded identity anchors",
            extra={
                "person_id": person_id,
                "soul_keys": list(soul_state.keys()) if isinstance(soul_state, dict) else [],
            },
        )

        # Guard: require any meaningful soul state before running.
        # Accept any populated soul_state dict — soul_refresh writes varied key shapes
        # (shadow/light/tone/identity_themes/core_values/friction depending on version).
        if not soul_state or len(soul_state) < 2:
            logger.info(
                "[identity_momentum] skipped: no identity signals",
                extra={"person_id": person_id, "soul_keys": list(soul_state.keys())},
            )
            return {}

        episodic_rows_raw = await q(
            """
            SELECT soul, emotional_state, rhythm_state, ts
            FROM memory_episodic
            WHERE person_id = $1
            ORDER BY ts DESC
            LIMIT 50
            """,
            person_id,
        )

        def normalize_episodic_row(row: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "soul": row.get("soul") or {},
                "emotional_state": row.get("emotional_state")
                or {"tone": "neutral", "valence": 0.0, "activation": 0.5, "stability": 0.5},
                "rhythm_state": row.get("rhythm_state")
                or {"energy_trend": "flat", "load_balance": "balanced", "recovery_signal": "unknown"},
                "ts": row.get("ts"),
            }

        # NOTE:
        # Episodic selection is intentionally naive in Phase-1.
        # Retrieval grounding and horizon gating are deferred.
        episodic = [normalize_episodic_row(r) for r in (episodic_rows_raw or [])]

        logger.info(
            "[identity_momentum_deep] episodic_inputs",
            extra={
                "person_id": person_id,
                "episodic_count": len(episodic),
                "with_emotion": sum(bool(r.get("emotional_state")) for r in episodic),
                "with_rhythm": sum(bool(r.get("rhythm_state")) for r in episodic),
            },
        )

        system_msg = (
            "You are Sakhi's Identity Momentum engine.\n"
            "Your task is to measure DIRECTIONAL MOMENTUM relative to the provided soul_state.\n"
            "Rules:\n"
            "- Do NOT infer identity, values, archetypes, or traits.\n"
            "- Do NOT give advice, recommendations, or coaching.\n"
            "- Do NOT write narrative prose.\n"
            "- Use soul_state only as a reference frame.\n"
            "- Analyze episodic evidence for consistency, drift, or oscillation.\n"
            "- If evidence is weak, say so explicitly.\n"
            "- Output ONLY valid JSON in the specified schema.\n"
            "Output schema (return exactly these keys):\n"
            "{ \"direction\": \"toward | away | oscillating | unclear\", \"magnitude\": 0.0, \"stability\": 0.0, \"confidence\": 0.0, \"evidence_summary\": \"...\", \"window_days\": 0 }"
        )
        def _default(o: Any):
            if hasattr(o, "isoformat"):
                return o.isoformat()
            return str(o)

        payload = {
            "soul_state": soul_state,
            "episodic_evidence": episodic,
            "emotion_state": emotion_state,
            "rhythm_state": rhythm_state,
        }
        user_msg = json.dumps(payload, ensure_ascii=False, default=_default)

        logger.info(
            "[identity_momentum] llm_request",
            extra={
                "person_id": person_id,
                "episodic_count": len(episodic),
            },
        )

        raw = await call_llm(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
        )

        try:
            parsed = json.loads(raw) if isinstance(raw, str) else (raw if isinstance(raw, dict) else {})
        except Exception:
            logger.error(
                "[identity_momentum] invalid JSON from LLM",
                extra={
                    "person_id": person_id,
                    "raw_preview": str(raw)[:200] if raw is not None else None,
                },
            )
            return {}

        if not parsed:
            logger.error(
                "[identity_momentum] empty result from LLM",
                extra={"person_id": person_id},
            )
            return {}

        required_keys = {"direction", "magnitude", "stability", "confidence", "evidence_summary", "window_days"}
        if not isinstance(parsed, dict) or not required_keys.issubset(parsed.keys()):
            logger.error(
                "[identity_momentum] missing required keys",
                extra={
                    "person_id": person_id,
                    "raw_preview": str(parsed)[:200],
                },
            )
            return {}

        await dbexec(
            """
            UPDATE personal_model
            SET identity_momentum_state = $2::jsonb,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            json.dumps(parsed, ensure_ascii=False),
        )

        logger.info(
            "[identity_momentum] updated",
            extra={
                "person_id": person_id,
                "episodes_used": len(episodic),
                "direction": parsed.get("direction"),
                "confidence": parsed.get("confidence"),
            },
        )

        return parsed
    except Exception as exc:  # pragma: no cover - diagnostic guard
        logger.error(
            "[identity_momentum] error",
            extra={"person_id": person_id, "error": str(exc)},
            exc_info=True,
        )
        return {}

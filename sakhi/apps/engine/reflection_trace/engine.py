from __future__ import annotations

import datetime
from typing import Any, Dict, Optional

def _safe_conf(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _blend_confidence(
    moment_model: Dict[str, Any],
    evidence_pack: Dict[str, Any],
    deliberation_scaffold: Optional[Dict[str, Any]],
) -> float:
    """
    Deterministic confidence blend:
      base weights: moment 0.4, evidence 0.4, deliberation 0.2
      if deliberation missing, redistribute proportionally.
    """
    mm = _safe_conf(moment_model.get("confidence"))
    ep = _safe_conf(evidence_pack.get("confidence"))
    deliv = _safe_conf(deliberation_scaffold.get("confidence")) if deliberation_scaffold else None

    if deliv is None:
        total_weight = 0.4 + 0.6  # redistribute deliberation weight equally to moment+evidence
        mm_w = 0.5
        ep_w = 0.5
        return (mm * mm_w) + (ep * ep_w)

    return (mm * 0.4) + (ep * 0.4) + (deliv * 0.2)


def build_reflection_trace(
    *,
    person_id: str,
    turn_id: str,
    session_id: Optional[str],
    moment_model: Dict[str, Any],
    evidence_pack: Dict[str, Any],
    deliberation_scaffold: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a deterministic, human-readable (non-interpretive) reflection trace.
    No LLM, no inference beyond supplied signals.
    """
    confidence = _blend_confidence(moment_model, evidence_pack, deliberation_scaffold)
    trace = {
        "turn_id": turn_id,
        "session_id": session_id,
        "moment_present": bool(moment_model),
        "evidence_present": bool(evidence_pack),
        "deliberation_present": deliberation_scaffold is not None,
        "moment_summary": {
            "stability": moment_model.get("stability"),
            "recommended_mode": moment_model.get("recommended_companion_mode"),
            "emotional_intensity": moment_model.get("emotional_intensity"),
        },
        "evidence_anchor_count": len((evidence_pack or {}).get("anchors") or []),
        "deliberation_summary": (deliberation_scaffold or {}).get("summary") if isinstance(deliberation_scaffold, dict) else None,
        "signals_used": {
            "moment": bool(moment_model),
            "evidence_pack": bool(evidence_pack),
            "deliberation_scaffold": deliberation_scaffold is not None,
        },
        "missing": [],
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }

    if not moment_model:
        trace["missing"].append("moment_model")
    if not evidence_pack:
        trace["missing"].append("evidence_pack")
    if deliberation_scaffold is None:
        trace["missing"].append("deliberation_scaffold")

    low_confidence = confidence < 0.3
    recommend_caution = confidence < 0.2

    return {
        "person_id": person_id,
        "turn_id": turn_id,
        "session_id": session_id,
        "moment_model": moment_model or {},
        "evidence_pack": evidence_pack or {},
        "deliberation_scaffold": deliberation_scaffold or {},
        "trace": trace,
        "confidence": confidence,
        "low_confidence": low_confidence,
        "recommend_caution": recommend_caution,
    }


async def persist_reflection_trace(db_exec, payload: Dict[str, Any]) -> None:
    """
    Best-effort upsert into reflection_traces.
    db_exec should mirror sakhi.apps.api.core.db.exec signature.
    """
    await db_exec(
        """
        INSERT INTO reflection_traces (
            person_id, turn_id, session_id,
            moment_model, evidence_pack, deliberation_scaffold, trace,
            confidence, low_confidence, recommend_caution
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (turn_id) DO UPDATE
        SET
            session_id = EXCLUDED.session_id,
            moment_model = EXCLUDED.moment_model,
            evidence_pack = EXCLUDED.evidence_pack,
            deliberation_scaffold = EXCLUDED.deliberation_scaffold,
            trace = EXCLUDED.trace,
            confidence = EXCLUDED.confidence,
            low_confidence = EXCLUDED.low_confidence,
            recommend_caution = EXCLUDED.recommend_caution
        """,
        payload["person_id"],
        payload["turn_id"],
        payload["session_id"],
        payload.get("moment_model") or {},
        payload.get("evidence_pack") or {},
        payload.get("deliberation_scaffold") or {},
        payload.get("trace") or {},
        float(payload.get("confidence") or 0.0),
        bool(payload.get("low_confidence")),
        bool(payload.get("recommend_caution")),
    )

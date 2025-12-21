from __future__ import annotations

import datetime
import hashlib
from typing import Any, Dict, Iterable, List, Tuple

from sakhi.apps.api.core.db import q


def _bucket_key(text: str) -> str:
    norm = (text or "").strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:8] if norm else ""


def _score_entry(idx: int, bucket_counts: Dict[str, int], entry: Dict[str, Any]) -> float:
    salience = float(entry.get("salience") or 0.5)
    recency = max(0.0, 1.0 - idx * 0.05)  # simple decay by rank
    bucket = entry.get("_bucket") or ""
    recurrence = 1.0 if bucket and bucket_counts.get(bucket, 0) > 1 else 0.0
    narrative_relevance = 0.6 if entry.get("arc_stage") else 0.0
    return (salience * 0.4) + (recency * 0.2) + (recurrence * 0.2) + (narrative_relevance * 0.2)


def _summarize_anchor(entry: Dict[str, Any], recurrence: bool) -> Tuple[str, str]:
    when = ""
    if entry.get("ts"):
        when = entry["ts"].isoformat() if hasattr(entry["ts"], "isoformat") else str(entry["ts"])
    what = (entry.get("text") or entry.get("what_happened") or "").strip()
    if not what:
        what = entry.get("title") or entry.get("summary") or ""
    why_bits = []
    if entry.get("arc_stage"):
        why_bits.append(f"showed up during {entry['arc_stage']}")
    if recurrence:
        why_bits.append("recurring signal")
    if entry.get("source") == "daily":
        why_bits.append("captured in daily reflection")
    why = "; ".join(why_bits) or "noted as a recent lived event"
    rec = "recurring" if recurrence else "contrast"
    return when, what, rec, why


async def select_evidence_anchors(person_id: str, limit: int = 30) -> Dict[str, Any]:
    """
    Build a deterministic EvidencePack for the current turn.
    No persistence. Safe, surface-level only.
    """
    anchors: List[Dict[str, Any]] = []
    sources_used: List[str] = []

    rows: List[Dict[str, Any]] = []
    try:
        episodic = await q(
            """
            SELECT ts, text, salience, arc_stage
            FROM memory_episodic
            WHERE person_id = $1
            ORDER BY ts DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
        for row in episodic:
            row = dict(row)
            row["_bucket"] = _bucket_key(row.get("text", ""))
            row["source"] = "episodic"
            rows.append(row)
        if episodic:
            sources_used.append("episodic")
    except Exception:
        pass

    try:
        daily = await q(
            """
            SELECT reflection_date, summary
            FROM daily_reflection_cache
            WHERE person_id = $1
            ORDER BY reflection_date DESC
            LIMIT 1
            """,
            person_id,
        )
        if daily:
            row = dict(daily[0])
            row["ts"] = row.get("reflection_date")
            row["text"] = row.get("summary")
            row["_bucket"] = _bucket_key(row.get("text", ""))
            row["arc_stage"] = None
            row["source"] = "daily"
            rows.append(row)
            sources_used.append("daily")
    except Exception:
        pass

    if not rows:
        return {
            "pattern_label": None,
            "confidence": 0.2,
            "anchors": [],
            "sources_used": [],
            "selection_reason": "fallback",
        }

    bucket_counts: Dict[str, int] = {}
    for r in rows:
        bucket = r.get("_bucket") or ""
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1 if bucket else bucket_counts.get(bucket, 0)

    scored = []
    for idx, row in enumerate(rows):
        score = _score_entry(idx, bucket_counts, row)
        scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)

    top = scored[:3] if scored else []
    final_anchors: List[Dict[str, Any]] = []
    for score, row in top:
        recurrence = (row.get("_bucket") or "") and bucket_counts.get(row.get("_bucket"), 0) > 1
        when, what, rec, why = _summarize_anchor(row, bool(recurrence))
        final_anchors.append(
            {
                "when": when,
                "what_happened": what,
                "why_it_matters": why,
                "recurrence_or_contrast": rec,
            }
        )

    selection_reason = "salience"
    if any(a["recurrence_or_contrast"] == "recurring" for a in final_anchors):
        selection_reason = "recurrence"
    if all(a["recurrence_or_contrast"] == "contrast" for a in final_anchors):
        selection_reason = "contrast"

    confidence = min(1.0, sum(s for s, _ in top) / max(len(top), 1)) if top else 0.2

    return {
        "pattern_label": None,
        "confidence": confidence,
        "anchors": final_anchors,
        "sources_used": sources_used,
        "selection_reason": selection_reason,
    }


__all__ = ["select_evidence_anchors"]

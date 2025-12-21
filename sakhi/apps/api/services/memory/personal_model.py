from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import dbfetchrow, exec as dbexec
from sakhi.apps.api.core.db import q
from sakhi.apps.engine.pattern_sense import engine as pattern_sense_engine


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.lower().strip().split())


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _blank_layers(now_iso: str) -> Dict[str, Any]:
    base = {"summary": None, "confidence": 0, "metrics": {}, "updated_at": None}
    return {
        "body": dict(base),
        "mind": dict(base),
        "emotion": dict(base),
        "goals": dict(base),
        "soul": dict(base),
    }


def _blank_identity_graph() -> Dict[str, Any]:
    return {
        "skills": [],
        "interests": [],
        "preferences": [],
        "values": [],
        "patterns": [],
    }


def _blank_model(now_iso: str) -> Dict[str, Any]:
    return {
        "person_id": None,
        "short_term": {
            "text": None,
            "layer": None,
            "observation": {"text": None, "layer": None},
            "updated_at": now_iso,
        },
        "long_term": {
            "layers": _blank_layers(now_iso),
            "identity_graph": _blank_identity_graph(),
            "observations": [],
            "merged_vector": [],
            "first_seen": now_iso,
            "updated_at": now_iso,
            "wellness_state": {},
        },
    }


def _average_vectors(existing: List[float], new: List[float], count_existing: int) -> List[float]:
    if not new:
        return existing
    if not existing or count_existing <= 0:
        return new
    n = min(len(existing), len(new))
    merged: List[float] = []
    total = count_existing + 1
    for i in range(n):
        merged.append(((existing[i] * count_existing) + new[i]) / total)
    return merged


async def update_personal_model(
    person_id: str,
    payload: Dict[str, Any],
    *,
    vector: List[float] | None = None,
    layer_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Canonical personal_model update (Build 51)
    - Dedup by normalized hash
    - Maintain canonical structure only
    """
    if not person_id:
        return {}
    if not isinstance(payload, dict):
        payload = {}

    raw_text = payload.get("text") or payload.get("user_text") or ""
    layer = payload.get("layer") or "conversation"
    entry_id = payload.get("entry_id")

    normalized_text = _normalize_text(raw_text)
    if not normalized_text:
        normalized_text = ""

    content_hash = _hash_text(normalized_text)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    existing = await dbfetchrow(
        """
        SELECT COALESCE(short_term, '{}'::jsonb) AS short_term,
               COALESCE(long_term, '{}'::jsonb)  AS long_term
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
    ) or {}

    def _coerce(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return dict(parsed)
            except json.JSONDecodeError:
                return {}
        return {}

    canonical = _blank_model(now_iso)
    canonical["person_id"] = person_id

    existing_short = _coerce(existing.get("short_term"))
    existing_long = _coerce(existing.get("long_term"))

    # Rebuild canonical long_term
    long_term = canonical["long_term"]
    existing_layers = {}
    if existing_long:
        # carry over observations/merged_vector/first_seen if present
        observations_existing = existing_long.get("observations") or []
        if isinstance(observations_existing, list):
            long_term["observations"] = [
                {k: obs.get(k) for k in ("entry_id", "text", "hash", "layer", "created_at")}
                for obs in observations_existing
                if isinstance(obs, dict)
            ]
        merged_vector_existing = existing_long.get("merged_vector")
        if isinstance(merged_vector_existing, list):
            long_term["merged_vector"] = merged_vector_existing
        first_seen_existing = existing_long.get("first_seen")
        if isinstance(first_seen_existing, str):
            long_term["first_seen"] = first_seen_existing
        identity_existing = existing_long.get("identity_graph")
        if isinstance(identity_existing, dict):
                long_term["identity_graph"] = {
                    "skills": identity_existing.get("skills") or [],
                    "interests": identity_existing.get("interests") or [],
                    "preferences": identity_existing.get("preferences") or [],
                    "values": identity_existing.get("values") or [],
                    "patterns": identity_existing.get("patterns") or [],
                }
        # Carry over narrative arc fields if present
        for arc_key in (
            "life_arcs",
            "micro_arcs",
            "active_arcs",
            "arc_states",
            "arc_progress",
            "arc_conflicts",
            "arc_breakthroughs",
            "active_goals_map",
            "identity_alignment_score",
        ):
            if arc_key in existing_long:
                long_term[arc_key] = existing_long.get(arc_key)
        layers_existing = existing_long.get("layers")
        if isinstance(layers_existing, dict):
            existing_layers = layers_existing
        # carry over wellness_state if present
        if isinstance(existing_long.get("wellness_state"), dict):
            long_term["wellness_state"] = existing_long.get("wellness_state")

    short_term = canonical["short_term"]
    if existing_short:
        short_term.update(
            {
                "text": existing_short.get("text"),
                "layer": existing_short.get("layer"),
                "observation": existing_short.get("observation") or short_term["observation"],
                "updated_at": existing_short.get("updated_at") or now_iso,
            }
        )

    observations: List[Dict[str, Any]] = [obs for obs in long_term.get("observations", []) if isinstance(obs, dict)]
    hashes = {obs.get("hash") for obs in observations if obs.get("hash")}
    is_new = content_hash not in hashes
    if is_new:
        observations.append(
            {
                "entry_id": entry_id,
                "text": normalized_text,
                "hash": content_hash,
                "layer": layer,
                "created_at": now_iso,
            }
        )
    long_term["observations"] = observations

    # merged vector recalculation using running average
    merged_vector = long_term.get("merged_vector") or []
    if is_new:
        merged_vector = _average_vectors(merged_vector, vector or [], len(observations) - 1)
    long_term["merged_vector"] = merged_vector

    # Enforce layer summaries to null/zero per Build 51, except soul uses stitched recent observations
    layers = _blank_layers(now_iso)
    # carry forward existing layers if present
    for key in layers.keys():
        if isinstance(existing_layers, dict) and existing_layers.get(key):
            current = existing_layers.get(key) or {}
            layers[key].update(
                {
                    "summary": current.get("summary"),
                    "confidence": current.get("confidence", 0),
                    "metrics": current.get("metrics") or {},
                    "updated_at": current.get("updated_at"),
                }
            )

    if observations:
        stitched = " ".join(obs.get("text") or "" for obs in observations[-5:]).strip()
        layers["soul"]["summary"] = layers["soul"]["summary"] or (stitched or None)
        layers["soul"]["updated_at"] = layers["soul"]["updated_at"] or now_iso
    if layer_overrides:
        for key in ("emotion", "mind", "soul"):
            if key in layer_overrides and isinstance(layer_overrides[key], dict):
                override = layer_overrides[key]
                layers[key].update(
                    {
                        "summary": override.get("summary"),
                        "confidence": override.get("confidence", layers[key]["confidence"]),
                        "metrics": override.get("metrics") or layers[key]["metrics"],
                        "updated_at": override.get("updated_at") or now_iso,
                    }
                )
    long_term["layers"] = layers
    # sync intents from intent_evolution
    try:
        intents_rows = await q(
            """
            SELECT intent_name, strength, trend, emotional_alignment, last_seen
            FROM intent_evolution
            WHERE person_id = $1
            """,
            person_id,
        )
        intents_payload = []
        for row in intents_rows or []:
            intents_payload.append(
                {
                    "name": row.get("intent_name"),
                    "strength": float(row.get("strength") or 0),
                    "trend": row.get("trend"),
                    "emotional_alignment": float(row.get("emotional_alignment") or 0),
                    "last_seen": row.get("last_seen"),
                }
            )
        long_term["intents"] = intents_payload
    except Exception:
        pass
    # carry emotion_state/wellness_state through if present and not overridden
    if isinstance(existing_long, dict):
        if existing_long.get("emotion_state") and "emotion_state" not in long_term:
            long_term["emotion_state"] = existing_long.get("emotion_state")
        if existing_long.get("wellness_state") and "wellness_state" not in long_term:
            long_term["wellness_state"] = existing_long.get("wellness_state")
        if existing_long.get("pattern_sense") and "pattern_sense" not in long_term:
            long_term["pattern_sense"] = existing_long.get("pattern_sense")

    # Short term snapshot
    short_term = {
        "text": normalized_text,
        "layer": layer,
        "observation": {"text": normalized_text, "layer": layer},
        "updated_at": now_iso,
    }

    long_term["updated_at"] = now_iso

    await dbexec(
        """
        INSERT INTO personal_model (person_id, short_term, long_term, updated_at)
        VALUES ($1, $2::jsonb, $3::jsonb, $4)
        ON CONFLICT (person_id)
        DO UPDATE SET
            short_term = EXCLUDED.short_term,
            long_term  = EXCLUDED.long_term,
            updated_at = EXCLUDED.updated_at
        """,
        person_id,
        json.dumps(short_term, ensure_ascii=False),
        json.dumps(long_term, ensure_ascii=False),
        now,
    )

    return {
        "person_id": person_id,
        "short_term": short_term,
        "long_term": long_term,
        "updated_at": now_iso,
    }


__all__ = [
    "update_personal_model",
    "_normalize_text",
    "_hash_text",
    "_blank_model",
    "_blank_layers",
    "_blank_identity_graph",
    "synthesize_layer",
]


def synthesize_layer(long_term: Dict[str, Any] | None, short_term: Dict[str, Any] | None, *, retention: int = 20) -> Dict[str, Any]:
    """
    Legacy compatibility shim. Returns a merged long_term object without altering canonical structure.
    """
    return long_term or {}

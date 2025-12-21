from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.clarity.confidence import anchor_confidence_from_provenance


async def compute_anchors(ctx: Dict[str, Any]) -> Dict[str, Any]:
    aspects = ctx["support"].get("aspects", [])
    anchors = {"time": None, "energy": None, "finance": None, "values": None}
    for aspect in aspects:
        if isinstance(aspect, dict):
            name = aspect.get("aspect")
            if name in anchors:
                anchors[name] = aspect.get("value")
        elif isinstance(aspect, str) and aspect in anchors:
            anchors[aspect] = True

    confidence = await anchor_confidence_from_provenance(ctx["person_id"])
    overall_conf = sum(confidence.values()) / max(1, len(confidence))
    return {"anchors": anchors, "confidence": confidence, "overall_confidence": overall_conf}

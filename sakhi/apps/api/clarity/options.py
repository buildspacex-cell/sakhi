from __future__ import annotations

from typing import Dict

from sakhi.apps.api.clarity.anchors import anchor_scores, clarity_score
from sakhi.apps.api.core.registry import ASPECTS


def _flatten_features(aspects_blob: dict) -> dict:
    flat: Dict[str, float] = {}
    for aspect_name, features in aspects_blob.items():
        for key, value in features.items():
            if isinstance(value, dict) and "score" in value:
                flat[f"{aspect_name}.{key}"] = float(value["score"])
            elif isinstance(value, (int, float)):
                flat[f"{aspect_name}.{key}"] = float(value)
    return flat


def _candidate_from_context(ctx: dict, label: str, changes: dict | None = None) -> dict:
    candidate = {"id": label, "plan": [], "notes": []}
    if changes:
        candidate.update(changes)
    return candidate


async def generate_options(person_id: str, ctx: dict) -> dict:
    A = _candidate_from_context(ctx, "A")
    B = _candidate_from_context(ctx, "B")
    C = _candidate_from_context(ctx, "C")

    for aspect in ASPECTS.values():
        for cand in (A, B, C):
            updated = aspect.adjust(cand, ctx)
            cand.update(updated)

    flat = _flatten_features(ctx.get("aspects", {}))
    anchors = await anchor_scores(person_id, ctx, flat)
    score = await clarity_score(person_id, anchors)

    return {
        "impact_panel": anchors,
        "score": score,
        "options": [A, B, C],
    }

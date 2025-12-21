from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.registry import register


class ValuesAspect:
    name = "values"

    async def fetch(self, msg: str, person_id: str, horizon: str) -> Dict[str, Any]:
        return {"alignment": 0.7}

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {"values_alignment": {"score": raw.get("alignment", 0.0)}}

    def score(self, candidate: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, float]:
        return {"values.alignment_score": candidate.get("values_alignment", {}).get("score", 0.0)}

    def adjust(self, candidate: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        return candidate

    def explain(self, candidate: Dict[str, Any], scores: Dict[str, float]) -> str:
        return "Aligned with your values."


register(ValuesAspect())

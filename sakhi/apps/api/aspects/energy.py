from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.registry import register

BEST = ["10:00-12:00", "15:00-17:00"]


class EnergyAspect:
    name = "energy"

    async def fetch(self, msg: str, person_id: str, horizon: str) -> Dict[str, Any]:
        return {"match": 0.8, "best": BEST, "recovery": 0.65}

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "chronotype_match": {"score": raw.get("match", 0.0), "best": raw.get("best", [])},
            "energy_slack": {"score": raw.get("recovery", 0.0)},
        }

    def score(self, candidate: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, float]:
        return {
            "energy.chronotype_match": candidate.get("chronotype_match", {}).get("score", 0.0),
            "energy.energy_slack": candidate.get("energy_slack", {}).get("score", 0.0),
        }

    def adjust(self, candidate: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        return candidate

    def explain(self, candidate: Dict[str, Any], scores: Dict[str, float]) -> str:
        return "Uses your high-focus windows."


register(EnergyAspect())

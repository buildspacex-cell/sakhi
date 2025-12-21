from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.registry import register


class TimeAspect:
    name = "time"

    async def fetch(self, msg: str, person_id: str, horizon: str) -> Dict[str, Any]:
        return {"slack_hours": 3.5, "busy": []}

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        slack = raw.get("slack_hours", 0.0)
        return {"time_slack": {"score": min(1.0, slack / 4.0), "hours": slack}}

    def score(self, candidate: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, float]:
        return {"time.time_slack": candidate.get("time_slack", {}).get("score", 0.0)}

    def adjust(self, candidate: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        return candidate

    def explain(self, candidate: Dict[str, Any], scores: Dict[str, float]) -> str:
        hours = candidate.get("time_slack", {}).get("hours", 0.0)
        return f"Fits into ~{hours:.1f}h of free time."


register(TimeAspect())

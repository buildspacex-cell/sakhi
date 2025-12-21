import json
import os
from typing import Any, Dict

try:  # pragma: no cover - defensive when router missing
    from sakhi.libs.llm_router.router import LLMRouter as Router  # type: ignore
except Exception:  # pragma: no cover
    Router = None

from sakhi.libs.schemas.db import get_async_pool

MODEL = os.getenv("MODEL_TOOL", os.getenv("MODEL_CHAT", "deepseek/deepseek-chat"))


async def propose_plan(intent_id: int, goal_text: str, horizon: str) -> Dict[str, Any]:
    router = Router() if Router else None
    msgs = [
        {
            "role": "system",
            "content": (
                "Propose 3–6 concrete milestones and this week's first 2–3 tasks. "
                "JSON: {milestones:[{title,target_date?}], week_tasks:[string]}"
            ),
        },
        {
            "role": "user",
            "content": f"Goal: {goal_text}\nHorizon: {horizon}",
        },
    ]
    data: Dict[str, Any]
    if router is not None:
        try:
            resp = await router.chat(messages=msgs, model=MODEL)
            data = json.loads(resp.text or "{}")
        except Exception:
            data = {}
    else:
        data = {}

    if not isinstance(data, dict):
        data = {}
    if "milestones" not in data or not isinstance(data.get("milestones"), list):
        data["milestones"] = [{"title": "Baseline setup"}]
    if "week_tasks" not in data or not isinstance(data.get("week_tasks"), list):
        data["week_tasks"] = ["Schedule baseline session"]

    pool = await get_async_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE intents SET proposed_plan=$2, status='clarifying' WHERE id=$1",
            intent_id,
            json.dumps(data),
        )
    return data


async def commit_plan(intent_id: int) -> Dict[str, Any]:
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, proposed_plan FROM intents WHERE id=$1",
            intent_id,
        )
        if row is None:
            return {"planned": False, "error": "intent_not_found"}
        _ = row["proposed_plan"] or {}
        await conn.execute(
            "UPDATE intents SET status='planned', user_permission=TRUE WHERE id=$1",
            intent_id,
        )
    return {"planned": True}

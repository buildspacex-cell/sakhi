import json
import os
from typing import Any, Dict, Optional

try:  # pragma: no cover - defensive guard when router deps unavailable
    from sakhi.libs.llm_router.router import LLMRouter as Router  # type: ignore
except Exception:  # pragma: no cover
    Router = None

MODEL = os.getenv("MODEL_TOOL", os.getenv("MODEL_CHAT", "deepseek/deepseek-chat"))

SYS = (
    "You are Sakhi's intent classifier. Distinguish INNER (feelings, reflections, awareness without action) "
    "from OUTER (any desire to do, plan, decide, or change something in the world, including habits or micro tasks).\n"
    "- Treat phrases like \"need to\", \"should\", \"have to\", \"going to\", \"plan to\", \"want to\", requests for help, "
    "and concrete activities (e.g., haircut, call mom, finish report) as OUTER.\n"
    "- INNER covers emotions, thoughts, memories, or observations without expressing an action.\n"
    "- When in doubt, prefer OUTER if there is any hint of actionability.\n"
    "Return STRICT JSON:\n"
    "{track:[inner,outer], share_type:[thought,feeling,story,goal,question],"
    " actionability:0..1, readiness:0..1,"
    " timeline:{horizon:[none,today,week,month,quarter,year,long_term,custom_date], target_date?:string},"
    " g_mvs:{target_horizon:bool,current_position:bool,constraints:bool,criteria:bool,assets_blockers:bool},"
    " emotion:[calm,joy,hope,anger,sad,anxious,stressed], sentiment:-1..1,"
    " tags:[strings], intent_type:[decision,goal,activity,habit,question,micro_task], domain?:string}"
)


def _heuristic_classification(text: str) -> Dict[str, Any]:
    lower = (text or "").lower()
    goal_markers = [
        "need to",
        "need",
        "should",
        "have to",
        "must",
        "plan to",
        "going to",
        "want to",
        "want",
        "plan",
        "become",
        "start",
        "launch",
        "build",
        "play",
        "goal",
        "grow",
        "create",
        "prepare",
        "wear",
    ]
    outer = any(marker in lower for marker in goal_markers)
    activity_markers = ["need", "haircut", "call", "email", "clean", "wash", "buy", "schedule"]
    activity = outer and any(marker in lower for marker in activity_markers)
    horizon = "none"
    if "year" in lower or "years" in lower:
        horizon = "long_term"
    elif "week" in lower:
        horizon = "week"

    domain = "career" if ("vp" in lower or "play" in lower) else "misc"

    return {
        "track": "outer" if outer else "inner",
        "share_type": "goal" if outer else "thought",
        "actionability": 0.8 if outer else 0.2,
        "readiness": 0.6,
        "timeline": {"horizon": horizon},
        "g_mvs": {
            "target_horizon": outer,
            "current_position": False,
            "constraints": False,
            "criteria": False,
            "assets_blockers": False,
        },
        "emotion": "calm",
        "sentiment": 0.0,
        "tags": [],
        "intent_type": "activity" if activity else ("goal" if outer else "question"),
        "domain": domain,
    }


async def classify_outer_inner(text: str, router: Optional[Any] = None) -> Dict[str, Any]:
    if Router is None and router is None:
        return _heuristic_classification(text)

    router_instance = router
    if router_instance is None:
        try:
            router_instance = Router()  # type: ignore[call-arg]
        except Exception:  # pragma: no cover
            router_instance = None
    if router_instance is None:
        return _heuristic_classification(text)

    msgs = [
        {"role": "system", "content": SYS},
        {"role": "user", "content": text + "\nJSON only."},
    ]
    try:
        resp = await router_instance.chat(messages=msgs, model=MODEL)
        return json.loads(resp.text or "{}")
    except Exception:
        return _heuristic_classification(text)

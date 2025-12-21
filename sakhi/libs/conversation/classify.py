import json
import os
import re
from typing import Any, Dict, Optional

try:  # pragma: no cover - allow running without router deps
    from sakhi.libs.llm_router.router import LLMRouter as Router  # type: ignore
except Exception:  # pragma: no cover
    Router = None  # fall back to stub

MODEL = os.getenv("MODEL_TOOL", os.getenv("MODEL_CHAT", "deepseek/deepseek-chat"))
SYS = (
    "Classify the user's last message. Return STRICT JSON: "
    "{dialog_act:[SHARE,ASK,DECIDE,PLAN,REPORT,VENT,SMALLTALK], "
    "topic:[work,health,relationships,learning,finance,other], "
    "goal_detected:bool, horizon:[none,short_term,medium_term,long_term,date], "
    "due_date?:string, info_gaps:[string], confidence:0..1}"
)


def _heuristic_classification(message: str) -> Dict[str, Any]:
    text = message or ""
    lower = text.lower()

    dialog_act = "SHARE"
    info_gaps: list[str] = []
    goal_detected = False

    if "?" in text:
        dialog_act = "ASK"
    elif any(keyword in lower for keyword in ("plan", "goal", "want to", "need to", "decide")):
        dialog_act = "PLAN"
        info_gaps = ["deadline", "constraints"]
        goal_detected = True
    elif any(keyword in lower for keyword in ("should", "choose", "decide")):
        dialog_act = "DECIDE"
        info_gaps = ["criteria", "tradeoff"]
        goal_detected = True

    topic = "other"
    topic_map = {
        "work": ["work", "job", "career", "office", "project"],
        "health": ["health", "sleep", "diet", "exercise", "workout"],
        "relationships": ["family", "partner", "friend", "relationship"],
        "learning": ["study", "learn", "course", "exam"],
        "finance": ["money", "budget", "income", "spend", "saving"],
    }
    for label, keywords in topic_map.items():
        if any(word in lower for word in keywords):
            topic = label
            break

    horizon = "none"
    due_date: Optional[str] = None
    if re.search(r"today|tonight", lower):
        horizon = "short_term"
    elif re.search(r"tomorrow|next (day|week)", lower):
        horizon = "short_term"
    elif re.search(r"next month|in \d+ weeks", lower):
        horizon = "medium_term"
    elif re.search(r"next year|in \d+ months", lower):
        horizon = "long_term"
    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", lower)
    if date_match:
        horizon = "date"
        due_date = date_match.group(0)

    confidence = 0.4
    return {
        "dialog_act": dialog_act,
        "topic": topic,
        "goal_detected": goal_detected,
        "horizon": horizon,
        "due_date": due_date,
        "info_gaps": info_gaps,
        "confidence": confidence,
    }


async def classify(message: str, router: Optional[Any] = None) -> Dict[str, Any]:
    if Router is None and router is None:
        return _heuristic_classification(message)

    router_instance = router
    if router_instance is None:
        try:
            router_instance = Router()  # type: ignore[call-arg]
        except Exception:  # pragma: no cover
            router_instance = None
    if router_instance is None:
        return _heuristic_classification(message)

    msgs = [
        {"role": "system", "content": SYS},
        {"role": "user", "content": message + "\nJSON only."},
    ]
    try:
        resp = await router_instance.chat(messages=msgs, model=MODEL)
        parsed = json.loads(resp.text or "{}")
        if isinstance(parsed, dict):
            parsed.setdefault("info_gaps", [])
            return parsed
        return _heuristic_classification(message)
    except Exception:
        return _heuristic_classification(message)

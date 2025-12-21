from __future__ import annotations

import re
from typing import Dict, List

FILLER_PREFIXES = [
    r"i want to",
    r"i need to",
    r"i should",
    r"i must",
    r"i plan to",
    r"i wish i could",
]

VERB_HINTS = [
    "buy",
    "fix",
    "join",
    "start",
    "learn",
    "upgrade",
    "clean",
    "improve",
    "reduce",
    "increase",
    "practice",
    "schedule",
]

HARMFUL_PATTERNS = ["harm", "suicide", "kill", "weapon"]
HEALTH_PATTERNS = ["medical", "diagnose", "prescription", "therapy"]
FINANCE_PATTERNS = ["investment", "crypto", "stocks", "loan", "mortgage"]


def normalize_intention(text: str) -> str:
    lower = (text or "").lower().strip()
    lower = re.sub(r"[\.!,;]+", "", lower)
    for prefix in FILLER_PREFIXES:
        lower = re.sub(rf"^{prefix}\s*", "", lower)
    lower = " ".join(lower.split())
    return lower


def _tag_energy(intent: str) -> str:
    if any(k in intent for k in ["learn", "read", "research"]):
        return "low"
    if any(k in intent for k in ["fix", "clean", "start"]):
        return "medium"
    return "medium"


def extract_micro_steps(text: str) -> List[Dict]:
    intent = normalize_intention(text)
    if not intent:
        return []

    # skip if the text is purely emotional/reflective without an action verb
    action_hints = VERB_HINTS + ["research", "figure", "purchase", "upgrade", "start", "fix", "clean"]
    if not any(hint in intent for hint in action_hints):
        return []

    steps: List[Dict] = []
    energy = _tag_energy(intent)

    # heuristic 3-5 atomic steps
    candidates = []
    if any(k in intent for k in ["learn", "research", "figure"]):
        candidates.append(("research basics", "research"))
    if any(k in intent for k in ["buy", "purchase", "upgrade"]):
        candidates.append(("list options", "prep"))
        candidates.append(("compare 2 options", "research"))
    candidates.append(("write one clear outcome", "prep"))
    candidates.append(("do a 5-minute first action", "action"))
    candidates.append(("note next follow-up", "followup"))

    for step, step_type in candidates[:5]:
        steps.append(
            {
                "step": step,
                "type": step_type,
                "difficulty": 2 if step_type in {"research", "prep"} else 3,
                "energy": energy,
                "emotion": None,
                "tags": [step_type],
            }
        )
    return steps


def score_confidence(text: str, steps: List[Dict]) -> float:
    base = 0.7
    intent = normalize_intention(text)
    tokens = intent.split()
    if any(h in intent for h in VERB_HINTS):
        base += 0.1
    # repeated tokens -> higher
    if len(set(tokens)) < max(1, len(tokens) // 2):
        base += 0.05
    if len(steps) >= 3:
        base += 0.05
    return max(0.4, min(0.95, base))


def is_blocked(text: str) -> bool:
    lower = (text or "").lower()
    for pat in HARMFUL_PATTERNS + HEALTH_PATTERNS + FINANCE_PATTERNS:
        if pat in lower:
            return True
    return False

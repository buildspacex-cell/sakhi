from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Mapping, Sequence

JOURNAL_LAYERS = ["body", "mind", "emotion", "soul", "goal"]


def _layer_prompt(layer: str, mood: str) -> str:
    templates = {
        "body": {
            "tired": "Scan your body from head to toe. Where is the fatigue loudest, and what would soothe it?",
            "anxious": "Locate the tension point. What ritual would help it loosen by 10%?",
            "default": "Notice your breathing and posture. What is your body telling you right now?",
        },
        "mind": {
            "tired": "Which thought loop is draining you? Name it so you can let it pass.",
            "anxious": "List the thoughts racing past. Which one deserves a gentle rebuttal?",
            "default": "What idea or question keeps circling in your mind this moment?",
        },
        "emotion": {
            "tired": "Name the feeling underneath the tiredness. What color or texture does it have?",
            "default": "Which emotion wants attention? Describe how it changes across this entry.",
        },
        "soul": {
            "tired": "Which value needs protection tonight?",
            "default": "How does this moment align with what you believe matters most?",
        },
        "goal": {
            "tired": "Which goal can rest tonight so you can return with more presence?",
            "default": "What small move would honor one of your active goals?",
        },
    }
    layer_templates = templates.get(layer, {})
    prompt = layer_templates.get(mood, layer_templates.get("default"))
    return prompt or "Write a few lines for this layer."


def _smart_prompt(mood: str, summary: str | None) -> str:
    if mood in {"sad", "tired"}:
        return "What is one gentle win from today that your future self should remember?"
    if mood == "anxious":
        return "List the signals your body gave you today—what did each try to protect?"
    if summary:
        return f"Given {summary[:80]}..., what shifted for you since the last entry?"
    return "What story is unfolding for you right now?"


def _triage_prompt(mood: str, text: str) -> Dict[str, Any]:
    crisis_keywords = ("panic", "overwhelmed", "burnout", "stuck")
    lowered = text.lower()
    for keyword in crisis_keywords:
        if keyword in lowered:
            return {
                "level": "high",
                "prompt": "Pause. Name the most intense sensation, rate it 1‑10, and note who could support you.",
            }
    if mood in {"sad", "angry", "anxious"}:
        return {
            "level": "medium",
            "prompt": "Before continuing, take one deep breath and name what needs comfort versus action.",
        }
    return {
        "level": "low",
        "prompt": "If everything feels steady, use this space to celebrate a micro-shift.",
    }


def _goal_prompt(context: Mapping[str, Any]) -> str:
    prefs: Sequence[Mapping[str, Any]] = context.get("prefs") or []
    for pref in prefs:
        if pref.get("kind") == "goal":
            title = pref.get("title") or pref.get("summary") or pref.get("goal")
            if title:
                return f"Link one sentence to your goal “{title}”. What progressed or drifted?"
    planner = context.get("planner") or {}
    goals = planner.get("goals") if isinstance(planner, dict) else []
    if isinstance(goals, list) and goals:
        first = goals[0]
        label = first.get("title") or first.get("label")
        if label:
            return f"Name one action that would move “{label}” forward this week."
    return "Name one intention this journal entry nudges forward."


def generate_journaling_guidance(
    *,
    user_id: str,
    text: str,
    tone: Mapping[str, Any],
    context: Mapping[str, Any],
    summary: str | None,
) -> Dict[str, Any]:
    mood = (tone.get("mood") or "neutral").lower()
    layer_prompts = [
        {
            "layer": layer,
            "prompt": _layer_prompt(layer, mood),
            "why": "let signals surface first" if layer in {"body", "emotion"} else "translate insight into direction",
        }
        for layer in JOURNAL_LAYERS
    ]
    goal_prompt = _goal_prompt(context)
    base_prompt = _smart_prompt(mood, summary)
    smart_prompts = [
        base_prompt,
        "Body → Mind → Emotion: write one sentence for each without editing.",
        "Finish with “What I really mean is…” and let the truth spill out.",
    ]
    triage = _triage_prompt(mood, text)
    go_deeper = "After writing, re-read and expand the boldest sentence with body + mind + emotion detail."
    if len(text.split()) < 40:
        go_deeper = "Entry is short. Add three more sentences describing senses, emotions, and desired shift."
    flow = "soothe" if mood in {"sad", "tired", "anxious"} else "activate"
    listening_passes = [
        {"phase": "landing", "instruction": "Name body + mood in 2 sentences."},
        {"phase": "explore", "instruction": "Follow the strongest thread across layers."},
        {"phase": "integrate", "instruction": "Link insight to a goal or ritual."},
    ]
    guidance = {
        "smart_prompts": smart_prompts,
        "primary_prompt": smart_prompts[0],
        "triage": triage,
        "goal_prompt": goal_prompt,
        "layer_prompts": layer_prompts,
        "flow": flow,
        "mood_route": "stabilize" if flow == "soothe" else "expand",
        "listening_passes": listening_passes,
        "multi_layer_order": JOURNAL_LAYERS,
        "nudges": [
            go_deeper,
            "End with one sentence for your future self (tomorrow or next week).",
            "If you feel stuck, switch pens or posture, then name the smallest win.",
        ],
        "mood": mood,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return guidance


__all__ = ["generate_journaling_guidance", "JOURNAL_LAYERS"]

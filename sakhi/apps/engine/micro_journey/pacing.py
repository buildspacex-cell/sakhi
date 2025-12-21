from __future__ import annotations

import datetime
from typing import Dict, List


def estimate_step_duration(step: Dict) -> int:
    """Deterministic duration in minutes based on keywords."""
    text = ""
    if isinstance(step, dict):
        text = " ".join(str(v).lower() for v in step.values() if isinstance(v, str))
    elif isinstance(step, str):
        text = step.lower()

    if any(k in text for k in ["clean", "water", "stretch", "prep"]):
        return 2
    if any(k in text for k in ["review", "organize", "read", "skim"]):
        return 5
    if any(k in text for k in ["plan", "write", "summarize", "focus"]):
        return 10
    if any(k in text for k in ["deep work", "creative block"]):
        return 15
    return 5


def estimate_flow_duration(flow: Dict) -> int:
    """Sum durations of steps plus a 1-minute transition."""
    steps = flow.get("steps") or []
    if not steps:
        steps = [
            {"text": flow.get("warmup_step", "")},
            {"text": flow.get("focus_block_step", "")},
            {"text": flow.get("closure_step", "")},
            {"text": flow.get("optional_reward", "")},
        ]

    total = 0
    for step in steps:
        duration = estimate_step_duration(step)
        if isinstance(step, dict):
            step["estimated_minutes"] = duration
        total += duration
    return total + 1  # transition minute


def apply_pacing(journey: Dict) -> Dict:
    """Attach pacing metadata to journey and flows."""
    flows: List[Dict] = journey.get("flows") or []
    total_minutes = 0
    for flow in flows:
        duration = estimate_flow_duration(flow)
        flow["estimated_minutes"] = duration
        total_minutes += duration
    structure = journey.get("structure") or {}
    structure["total_estimated_minutes"] = total_minutes
    start_at = journey.get("generated_at") or datetime.datetime.utcnow().isoformat()
    try:
        start_dt = datetime.datetime.fromisoformat(str(start_at))
    except Exception:
        start_dt = datetime.datetime.utcnow()
    end_dt = start_dt + datetime.timedelta(minutes=total_minutes)
    structure["pacing"] = {
        "start_at": start_dt.isoformat(),
        "end_at_estimated": end_dt.isoformat(),
        "breathing_points": [
            {"after_flow": 1, "pause_seconds": 20},
            {"after_flow": 2, "pause_seconds": 20},
        ],
    }
    journey["structure"] = structure
    return journey


__all__ = [
    "estimate_step_duration",
    "estimate_flow_duration",
    "apply_pacing",
]

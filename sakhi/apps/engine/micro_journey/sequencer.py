from __future__ import annotations

from typing import Dict, List


LOW_EFFORT_KEYWORDS = {"clean", "water", "stretch", "check", "tidy"}
MID_EFFORT_KEYWORDS = {"review", "organize", "summarize"}
HIGH_EFFORT_KEYWORDS = {"plan", "write", "focus block"}
VERY_HIGH_EFFORT_KEYWORDS = {"deep work", "creative block"}


def compute_flow_effort(flow: Dict) -> int:
    """Deterministic effort score based on text keywords."""
    text_parts: List[str] = []
    for key in ("warmup_step", "focus_block_step", "closure_step", "optional_reward"):
        val = flow.get(key)
        if isinstance(val, str):
            text_parts.append(val.lower())
    text = " ".join(text_parts)
    score = 1
    if any(k in text for k in VERY_HIGH_EFFORT_KEYWORDS):
        score = 4
    elif any(k in text for k in HIGH_EFFORT_KEYWORDS):
        score = 3
    elif any(k in text for k in MID_EFFORT_KEYWORDS):
        score = 2
    elif any(k in text for k in LOW_EFFORT_KEYWORDS):
        score = 1
    return score


def reorder_flows(flows: List[Dict], rhythm_slot: str) -> List[Dict]:
    """Sort flows by effort with rhythm overrides; stable for equal effort."""
    decorated = []
    for idx, flow in enumerate(flows):
        effort = compute_flow_effort(flow)
        decorated.append((effort, idx, flow))

    # base sort by effort then original index for stability
    decorated.sort(key=lambda item: (item[0], item[1]))

    reordered = [f for _, _, f in decorated]

    if rhythm_slot in {"evening", "night"}:
        heavy = [f for f in reordered if compute_flow_effort(f) >= 3]
        light = [f for f in reordered if compute_flow_effort(f) < 3]
        reordered = light + heavy
    elif rhythm_slot == "morning":
        planning_keywords = ("plan", "write", "organize")
        planning_flows = []
        other_flows = []
        for f in reordered:
            text = " ".join([str(v).lower() for v in f.values() if isinstance(v, str)])
            if any(k in text for k in planning_keywords):
                planning_flows.append(f)
            else:
                other_flows.append(f)
        reordered = planning_flows + other_flows

    return reordered


def apply_adaptive_sequencing(journey: Dict) -> Dict:
    flows = journey.get("flows") or []
    rhythm_slot = journey.get("rhythm_slot") or "morning"
    reordered = reorder_flows(flows, rhythm_slot)
    journey["flows"] = reordered
    structure = journey.get("structure") or {}
    structure["reordered"] = True
    structure["rules_used"] = [
        "effort_sorting",
        "rhythm_overrides",
        "stable_ordering",
    ]
    journey["structure"] = structure
    return journey


__all__ = ["compute_flow_effort", "reorder_flows", "apply_adaptive_sequencing"]

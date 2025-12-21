from __future__ import annotations

def early_stage(arc_name: str) -> str:
    return f"Early stage: {arc_name}"


def momentum_arc(arc_name: str) -> str:
    return f"Momentum increasing in {arc_name}"


def tension_arc(arc_name: str) -> str:
    return f"Tension detected in {arc_name}"


def breakthrough_arc(arc_name: str) -> str:
    return f"Breakthrough in {arc_name}"


__all__ = ["early_stage", "momentum_arc", "tension_arc", "breakthrough_arc"]

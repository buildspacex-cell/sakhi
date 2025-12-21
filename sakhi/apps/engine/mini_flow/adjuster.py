from __future__ import annotations

import datetime
from typing import Dict


def determine_rhythm_slot(now_dt: datetime.datetime) -> str:
    hour = now_dt.hour
    if 4 <= hour < 11:
        return "morning"
    if 11 <= hour < 15:
        return "midday"
    if 15 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    return "night"


def adjust_mini_flow(flow: Dict[str, str], rhythm_slot: str) -> Dict[str, str]:
    adjusted = dict(flow)
    if rhythm_slot == "morning":
        adjusted["warmup_step"] = "Quick 1-minute setup."
        adjusted["focus_block_step"] = f"{flow.get('focus_block_step') or ''} (continue for ~10 minutes).".strip()
    elif rhythm_slot == "midday":
        adjusted["warmup_step"] = f"{flow.get('warmup_step') or ''} (take 60 seconds).".strip()
    elif rhythm_slot == "afternoon":
        adjusted["warmup_step"] = f"{flow.get('warmup_step') or ''} (light reset for 1 minute).".strip()
        adjusted["closure_step"] = "Wrap the block and note one next-step."
    elif rhythm_slot == "evening":
        adjusted["warmup_step"] = "Brief 30-second setup."
        adjusted["focus_block_step"] = f"{flow.get('focus_block_step') or ''} (keep it short ~5 minutes).".strip()
        adjusted["closure_step"] = "Close gently and note if continuation is needed tomorrow."
    else:  # night
        adjusted["warmup_step"] = "Minimal 30-second setup only."
        adjusted["focus_block_step"] = "Do a <2-minute continuation check (no deep focus)."
        adjusted["closure_step"] = "Stop for today."
        adjusted["optional_reward"] = ""
    return adjusted


__all__ = ["determine_rhythm_slot", "adjust_mini_flow"]

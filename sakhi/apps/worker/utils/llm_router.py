from __future__ import annotations

from typing import Dict

from sakhi.apps.worker.utils.db import db_fetch


def compose_prompt(person_id: str, base_prompt: str) -> str:
    """
    Compose a prompt injected with tone hints derived from prompt_profiles.
    """
    profile = db_fetch("prompt_profiles", {"person_id": person_id}) or {}
    tone: Dict[str, float] = profile.get("tone_weights") or {"warm": 0.5, "direct": 0.5}
    warm = float(tone.get("warm", 0.5))
    direct = float(tone.get("direct", 0.5))
    tone_hint = "gentle" if warm >= direct else "clear"
    return f"[Tone:{tone_hint}] {base_prompt}"


__all__ = ["compose_prompt"]

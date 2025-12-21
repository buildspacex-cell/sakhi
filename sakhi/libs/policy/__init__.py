from __future__ import annotations

import os
from functools import lru_cache
import yaml


class PolicyLoader:
    def __init__(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            self.data = yaml.safe_load(fh) or {}

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def get_ack(self, key: str) -> str:
        templates = self.data.get("ack_templates", {}) or {}
        return templates.get(key, templates.get("neutral", "Got it."))

    def get_ack_by_emotion(self, emotion: str, fallback: str = "neutral") -> str:
        """
        Looks up an acknowledgement by fine-grained emotion label or alias.
        """
        emotion = (emotion or "").lower()
        tones = self.data.get("ack_tones", {}) or {}

        if emotion in tones:
            return tones[emotion]

        for key in tones:
            if key in emotion:
                return tones[key]

        key = "positive" if emotion in {"happy", "excited"} else (
            "heavy" if emotion in {"sad", "tired", "overwhelmed"} else fallback
        )
        return self.get_ack(key)


@lru_cache(maxsize=1)
def load_policy() -> PolicyLoader:
    base = os.path.join(os.path.dirname(__file__), "conversation.yaml")
    return PolicyLoader(os.path.abspath(base))


__all__ = ["PolicyLoader", "load_policy"]

from __future__ import annotations

from typing import Dict, List, Tuple


def summarize_layers(trace_events: List[dict]) -> Tuple[str, List[dict]]:
    """Turn trace events into a narration and a structured layer summary."""

    layers: List[dict] = []
    narration_parts: List[str] = []

    for event in trace_events:
        stage = event.get("stage")
        label = event.get("label")
        payload = event.get("payload") or event.get("data") or {}

        if stage == "extract":
            intents = payload.get("intents")
            domains = payload.get("domains")
            intent_label = intents or "an intent"
            domain_label = domains or "general context"
            message = f"I recognised this as {intent_label} in {domain_label}."
        elif stage == "metrics":
            salience = payload.get("salience")
            significance = payload.get("significance")
            message = "I updated salience and significance."
            if salience is not None or significance is not None:
                message = (
                    f"I updated salience to {salience} and significance to {significance}."
                )
        elif stage == "recall":
            candidates = payload.get("candidates") or [{}]
            top_keys = [candidate.get("key") for candidate in candidates[:2] if candidate.get("key")]
            if top_keys:
                message = f"I recalled related memories: {', '.join(top_keys)}."
            else:
                message = "I looked for related memories."
        elif stage == "prompt":
            message = "I built a reasoning prompt for the LLM using your context and recalled memories."
        elif stage == "llm":
            finish_reason = payload.get("finish_reason", "complete")
            tokens_out = payload.get("tokens_out", 0)
            message = f"The LLM replied ({finish_reason}) with {tokens_out} tokens."
        else:
            message = f"{stage}:{label}"

        layers.append({"layer": stage, "summary": message, "payload": payload})
        narration_parts.append(message)

    return " ".join(narration_parts), layers


__all__ = ["summarize_layers"]

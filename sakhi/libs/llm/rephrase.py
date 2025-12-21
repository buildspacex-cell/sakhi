"""Acknowledgement rephrase helper (placeholder)."""

from typing import Optional


def rephrase_ack_llm(text: str, system_prompt: str, router: Optional[object] = None) -> str:
    """
    Attempt to rephrase an acknowledgement line using an LLM router.
    Temporarily returns the original text until an inference backend is hooked in.
    """
    return text

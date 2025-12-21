from __future__ import annotations

import logging
from typing import Dict, List

from sakhi.libs.llm_router import LLMRouter, Task
from sakhi.libs.llm_router.openai_provider import make_openai_provider_from_env
from sakhi.libs.llm_router.openrouter import OpenRouterProvider
from sakhi.libs.schemas import get_settings

SUMMARY_SYS = """You are Sakhi's Brain layer. Summarize recent turns into a crisp rolling context:
- Key goals/decisions
- Open threads (with 1-line status)
- Constraints/preferences detected (time, budget, locations)
- Current tone/mood trend
Keep it under 180 words. Bullet points allowed.
"""

_LOGGER = logging.getLogger(__name__)
_BASE_SYSTEM = "You are Sakhi. Keep the rolling context grounded and coherent."
_SUMMARY_MODEL = "gpt-4o-mini"
_ROUTER: LLMRouter | None = None


def build_summary_prompt(summary: str, recent: List[Dict]) -> str:
    turns = "\n".join(f"{turn['role'].capitalize()}: {turn['text']}" for turn in recent)
    return f"{SUMMARY_SYS}\nPrevious summary:\n{summary}\nRecent turns:\n{turns}\nNew summary:"


def _ensure_router() -> LLMRouter:
    global _ROUTER
    if _ROUTER is not None:
        return _ROUTER

    settings = get_settings()
    router = LLMRouter()
    providers: list[str] = []

    openai_provider = make_openai_provider_from_env()
    if openai_provider:
        router.register_provider('openai', openai_provider)
        providers.append('openai')

    api_key = settings.openrouter_api_key
    if api_key:
        provider = OpenRouterProvider(api_key=api_key)
        router.register_provider('openrouter', provider)
        providers.append('openrouter')

    if not providers:
        _LOGGER.warning("No summary provider configured; falling back to heuristic summary")
        return None

    router.set_policy(Task.CHAT, providers)
    _ROUTER = router
    return router


async def roll_summary(summary: str, recent: List[Dict]) -> str:
    prompt = build_summary_prompt(summary, recent)
    router = _ensure_router()
    if router is None:
        merged = summary or ""
        for turn in recent[-5:]:
            merged += f"\n{turn['role'].capitalize()}: {turn['text']}"
        return merged.strip()[:400]
    response = await router.chat(
        messages=[
            {'role': 'system', 'content': f"{_BASE_SYSTEM}\n\n{SUMMARY_SYS}"},
            {'role': 'user', 'content': prompt},
        ],
        model=_SUMMARY_MODEL,
    )
    return response.text or ''

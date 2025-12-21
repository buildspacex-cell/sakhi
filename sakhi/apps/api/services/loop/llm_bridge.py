from __future__ import annotations

import os
from typing import Any, Mapping

from sakhi.libs.llm_router import LLMRouter, OpenRouterProvider, Task
from sakhi.libs.llm_router.openai_provider import make_openai_provider_from_env
from sakhi.libs.schemas import get_settings

from .prompt import SYSTEM, build_prompt
from sakhi.libs.prompt_builder import build_prompt as build_person_prompt

_ROUTER: LLMRouter | None = None


def _ensure_router() -> LLMRouter:
    global _ROUTER
    if _ROUTER is not None:
        return _ROUTER

    settings = get_settings()
    router = LLMRouter()
    providers: list[str] = []

    openai_provider = make_openai_provider_from_env()
    if openai_provider:
        router.register_provider("openai", openai_provider)
        providers.append("openai")

    api_key = settings.openrouter_api_key or os.getenv("LLM_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL")
    tenant = os.getenv("OPENROUTER_TENANT")
    if api_key:
        provider = OpenRouterProvider(api_key=api_key, base_url=base_url, tenant=tenant)
        router.register_provider("openrouter", provider)
        providers.append("openrouter")

    if not providers:
        raise RuntimeError("No LLM provider configured for loop service")

    router.set_policy(Task.CHAT, providers)
    router.set_policy(Task.TOOL, providers)
    _ROUTER = router
    return router


async def talk_with_objective(
    user_id: str,
    text: str,
    ctx: Mapping[str, Any],
    objective: str,
    clarity_hint: str | None = None,
) -> str:
    router = _ensure_router()
    personal_model_context: str | None = None
    try:
        personal_model_context = await build_person_prompt(user_id, text)
    except Exception:
        personal_model_context = None
    prompt = build_prompt(
        text,
        ctx,
        objective,
        clarity_hint=clarity_hint,
        personal_model_context=personal_model_context,
    )
    model_name = os.getenv("MODEL_CHAT", "gpt-4o-mini")
    response = await router.chat(
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": prompt,
                "name": f"user_{user_id}",
            },
        ],
        model=model_name,
    )
    return response.text or ""

"""Policy-aware LLM router with provider budgeting."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping, MutableMapping, Sequence

from .base import BaseProvider
from .types import LLMResponse, Task


def _format_persona_prompt(persona: str) -> str:
    """Create a system prompt line reinforcing the requested persona archetype."""
    persona_clean = persona.strip() or "companion"
    return (
        f"Persona archetype: {persona_clean}. Embody this voice while remaining grounded, warm, "
        "and attentive to the person's rhythms."
    )


class BudgetExceededError(RuntimeError):
    """Raised when a provider's daily budget has been exhausted."""


@dataclass
class DailyBudget:
    """Tracks provider spend with automatic daily resets."""

    limit: float | None
    spent: float = 0.0
    day: date = field(default_factory=date.today)

    def register(self, amount: float, *, provider: str) -> None:
        """Record spend, enforcing the configured limit."""

        if amount is None or amount <= 0:
            self._rollover_if_needed()
            return

        self._rollover_if_needed()
        if self.limit is not None and self.spent + amount > self.limit:
            raise BudgetExceededError(
                f"Daily budget exceeded for provider '{provider}': "
                f"{self.spent + amount:.4f} > {self.limit:.4f}"
            )
        self.spent += amount

    def _rollover_if_needed(self) -> None:
        today = date.today()
        if today != self.day:
            self.day = today
            self.spent = 0.0


@dataclass
class LLMRouteConfig:
    """Configuration payload controlling provider selection and budgets."""

    policy: dict[Task, list[str]] = field(default_factory=dict)
    provider_budgets: dict[str, float | None] = field(default_factory=dict)


class LLMRouter:
    """Orchestrate LLM requests across configurable providers."""

    def __init__(
        self,
        *,
        config: LLMRouteConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._logger = logger or logging.getLogger(__name__)
        self._config = config or LLMRouteConfig()
        self._budgets: MutableMapping[str, DailyBudget] = {
            name: DailyBudget(limit)
            for name, limit in self._config.provider_budgets.items()
        }

    def register_provider(
        self,
        key: str,
        provider: BaseProvider,
        *,
        daily_budget: float | None = None,
    ) -> None:
        """Register or update a provider, optionally overriding its daily budget."""

        self._providers[key] = provider
        if daily_budget is not None:
            self._budgets[key] = DailyBudget(daily_budget)
        elif key not in self._budgets:
            limit = self._config.provider_budgets.get(key)
            self._budgets[key] = DailyBudget(limit)

    def set_policy(self, task: Task, providers: Sequence[str]) -> None:
        """Assign an ordered list of providers for the given task."""

        if not providers:
            raise ValueError("Provider policy requires at least one provider key")
        self._config.policy[task] = list(dict.fromkeys(providers))

    async def chat(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        model: str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute a chat request with automatic provider failover."""

        message_payload = [dict(message) for message in messages]
        persona = kwargs.pop("persona", None)
        persona_prompt = _format_persona_prompt(str(persona)) if persona else None
        if message_payload and message_payload[0].get("role") == "system":
            sys_msg = dict(message_payload[0])
            existing = (sys_msg.get("content") or "").strip()
            if persona_prompt and persona_prompt not in existing:
                sep = "\n\n" if existing else ""
                sys_msg["content"] = f"{existing}{sep}{persona_prompt}"
            message_payload[0] = sys_msg
        elif persona_prompt:
            message_payload.insert(0, {"role": "system", "content": persona_prompt})

        tool_payload = list(tools) if tools else None
        task = Task.TOOL if tools else Task.CHAT
        errors: list[str] = []
        for candidate in self._resolve_candidates(task, provider_override=provider):
            try:
                return await self._execute(
                    task,
                    candidate,
                    call_kwargs={"messages": message_payload, "model": model, "tools": tool_payload, **kwargs},
                )
            except Exception as exc:
                self._logger.warning(
                    "Provider %s failed for %s task: %s", candidate, task.value, exc, exc_info=True
                )
                errors.append(f"{candidate}: {exc}")
                continue
        raise RuntimeError(f"All providers failed for task '{task.value}': {'; '.join(errors)}")

    async def embed(
        self,
        *,
        inputs: Sequence[str],
        model: str,
        provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute an embedding request with automatic provider failover."""

        raise RuntimeError(
            "Embeddings are not routed via providers. "
            "Use sakhi.libs.embeddings.embed_text(text) instead of router.embed()."
        )

    async def _execute(
        self,
        task: Task,
        provider_key: str,
        *,
        call_kwargs: dict[str, Any],
    ) -> LLMResponse:
        provider = self._providers.get(provider_key)
        if provider is None:
            raise ValueError(f"Provider '{provider_key}' is not registered")

        response = await provider.chat(**call_kwargs)

        if response.provider is None:
            response.provider = provider_key
        self._apply_budget(provider_key, response.cost)
        self._log_usage(provider_key, response)
        return response

    def _resolve_provider(self, task: Task, *, provider_override: str | None) -> str:
        candidates = self._resolve_candidates(task, provider_override=provider_override)
        if not candidates:
            raise ValueError(f"No providers configured for task '{task.value}'")
        return candidates[0]

    def _resolve_candidates(self, task: Task, *, provider_override: str | None) -> list[str]:
        """Return providers for the given task in priority order."""

        if provider_override:
            if provider_override not in self._providers:
                raise ValueError(f"Override provider '{provider_override}' is not registered")
            return [provider_override]

        if task not in (Task.CHAT, Task.TOOL):
            raise ValueError(
                f"Task '{task.value}' is not routed. Use embed_text() for embeddings."
            )

        candidates = self._config.policy.get(task)
        if not candidates:
            raise ValueError(f"No providers configured for task '{task.value}'")

        resolved = [candidate for candidate in candidates if candidate in self._providers]
        if not resolved:
            raise ValueError(f"No registered providers available for task '{task.value}'")
        return resolved

    def _apply_budget(self, provider_key: str, cost: float | None) -> None:
        tracker = self._budgets.get(provider_key)
        if tracker is None:
            tracker = DailyBudget(self._config.provider_budgets.get(provider_key))
            self._budgets[provider_key] = tracker
        tracker.register(cost or 0.0, provider=provider_key)

    def _log_usage(self, provider_key: str, response: LLMResponse) -> None:
        usage = response.usage or {}
        self._logger.info(
            "llm_task=%s provider=%s model=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s cost=%.6f",
            response.task.value,
            provider_key,
            response.model,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
            (response.cost or 0.0),
        )


__all__ = ["BudgetExceededError", "DailyBudget", "LLMRouteConfig", "LLMRouter"]


if __name__ == "__main__":  # pragma: no cover - manual demo
    import asyncio
    import os

    async def _demo() -> None:
        from .openrouter import OpenRouterProvider
        from .types import Task

        logging.basicConfig(level=logging.INFO)
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_API_KEY environment variable is required for the demo")

        model = os.environ.get("MODEL_CHAT", "deepseek/deepseek-chat")
        base_url = os.environ.get("LLM_BASE_URL")

        router = LLMRouter()
        router.set_policy(Task.CHAT, ["openrouter"])
        router.set_policy(Task.TOOL, ["openrouter"])

        provider = OpenRouterProvider(api_key=api_key, base_url=base_url)
        router.register_provider("openrouter", provider)

        response = await router.chat(
            messages=[{"role": "user", "content": "Say hello from DeepSeek."}],
            model=model,
        )
        print(response.text or "[no text returned]")

    asyncio.run(_demo())

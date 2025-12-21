import asyncio
from typing import Any, Dict

import pytest

from sakhi.libs.llm_router.base import BaseProvider
from sakhi.libs.llm_router.router import LLMRouter
from sakhi.libs.llm_router.types import LLMResponse, Task
from sakhi.libs.schemas.tools import CREATE_PLAN_TOOL


class DummyProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="dummy")

    async def chat(self, *, messages, model: str, tools=None, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            model=model,
            task=Task.TOOL,
            tool_calls=[
                {
                    "name": "create_plan",
                    "arguments": {"objective": "Prepare talk", "horizon": "Nov 10"},
                }
            ],
            provider=self.name,
            usage={"provider": self.name},
        )

    async def embed(self, *, inputs, model: str, **kwargs: Any) -> LLMResponse:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_router_tool_call_normalization() -> None:
    router = LLMRouter()
    router.register_provider("dummy", DummyProvider())
    router.set_policy(Task.CHAT, ["dummy"])
    router.set_policy(Task.TOOL, ["dummy"])

    response = await router.chat(messages=[{"role": "user", "content": "Plan"}], model="dummy-model", tools=[CREATE_PLAN_TOOL])

    assert response.tool_calls is not None
    call = response.tool_calls[0]
    assert call["name"] == "create_plan"
    assert call["arguments"]["objective"] == "Prepare talk"

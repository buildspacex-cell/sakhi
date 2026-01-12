"""Run the narrative_deep worker for a person (defaults to demo user)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sakhi.apps.api.core.llm import set_router
from sakhi.apps.worker.narrative_deep import generate_deep_soul_narrative
from sakhi.libs.llm_router.router import LLMRouter, LLMRouteConfig
from sakhi.libs.llm_router.openai_provider import OpenAIProvider
from sakhi.libs.llm_router.types import Task


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run narrative_deep for a person.")
    parser.add_argument(
        "--person-id",
        default="c10fbd98-25fa-4445-8aba-e5243bc01564",
        help="Person ID to run narrative_deep for (defaults to demo user).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Initialize a minimal router for local runs.
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to run narrative_deep")
    router = LLMRouter(config=LLMRouteConfig(policy={Task.CHAT: ["openai"]}))
    router.register_provider("openai", OpenAIProvider(api_key=api_key, model_chat=os.getenv("MODEL_CHAT") or "gpt-4o-mini"))
    set_router(router)

    logging.info("Starting narrative_deep for person_id=%s", args.person_id)
    result = await generate_deep_soul_narrative(args.person_id)
    try:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:  # pragma: no cover - defensive
        logging.error("Failed to dump result as JSON: %s", exc)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())

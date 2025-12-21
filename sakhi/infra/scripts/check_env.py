"""Validate presence of critical environment variables."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

REQUIRED_VARS = (
    "DATABASE_URL",
    "REDIS_URL",
    "OPENROUTER_API_KEY",
    "LLM_ROUTER",
    "MODEL_CHAT",
    "MODEL_TOOL",
    "MODEL_REFLECT",
    "MODEL_EMBED",
)


PLACEHOLDER_VALUES = {
    "OPENROUTER_API_KEY": {"replace_me"},
}


def main() -> None:
    load_dotenv(override=False)

    missing: list[str] = []
    for name in REQUIRED_VARS:
        value = os.getenv(name)
        if not value:
            missing.append(name)
            continue

        placeholder_values = PLACEHOLDER_VALUES.get(name, set())
        if value in placeholder_values:
            missing.append(name)

    if missing:
        for name in missing:
            print(f"Missing or invalid environment variable: {name}")
        sys.exit(1)

    print("Environment variables look good.")


if __name__ == "__main__":  # pragma: no cover
    main()

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

BASE_DIR = Path(__file__).resolve().parents[4]
PROMPT_DIR = Path(os.environ.get("SAKHI_PROMPTS_DIR", BASE_DIR / "config" / "prompts"))
POLICY_DIR = Path(os.environ.get("SAKHI_POLICY_DIR", BASE_DIR / "config" / "policy"))

_CACHE: Dict[Tuple[str, str], Tuple[float, Any]] = {}
_IS_PROD = os.getenv("SAKHI_ENVIRONMENT", "development").lower() in {"prod", "production"}
_HOT_RELOAD = os.getenv("SAKHI_CONFIG_HOT", "1" if not _IS_PROD else "0").lower() in {"1", "true", "yes", "on"}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load(kind: str, name: str, directory: Path, loader) -> Any:
    path = directory / name
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    cache_key = (kind, str(path))
    mtime = path.stat().st_mtime
    if not _HOT_RELOAD:
        cached = _CACHE.get(cache_key)
        if cached and (_IS_PROD or cached[0] == mtime):
            return cached[1]

    data = loader(path)
    if not _HOT_RELOAD:
        _CACHE[cache_key] = (mtime, data)
    return data


def get_prompt(name: str) -> Dict[str, Any]:
    filename = name if name.endswith(".json") else f"{name}.json"
    data = _load("prompt", filename, PROMPT_DIR, _load_json)
    if not isinstance(data, dict):
        raise ValueError(f"Prompt '{name}' must be a JSON object")
    return data


def get_policy(name: str) -> Dict[str, Any]:
    filename = name if name.endswith(".yml") or name.endswith(".yaml") else f"{name}.yml"
    data = _load("policy", filename, POLICY_DIR, _load_yaml)
    if not isinstance(data, dict):
        raise ValueError(f"Policy '{name}' must be a YAML object")
    return data

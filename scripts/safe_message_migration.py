"""
Safe helper for tagging and replacing user-facing send_message() calls
with dynamic compose_response() calls.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
from typing import Dict, Iterable

# --- CONFIG ---
SEARCH_DIRS = ["apps/api/routes", "apps/worker/tasks"]
INTENT_MAP: Dict[str, str] = {
    "add this as a task": "confirm_task_creation",
    "set a date": "ask_due_date",
    "refine future reflections": "acknowledge_feedback",
    "updated it": "acknowledge_update",
    "earlier": "reflective_nudge",
}
BACKUP_SUFFIX = ".bak"
IMPORT_LINE = "from apps.worker.utils.response_composer import compose_response"


def tag_and_preview() -> None:
    for base in SEARCH_DIRS:
        for path in pathlib.Path(base).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            matches = re.findall(r'send_message\(["\'](.+?)["\']\)', text)
            if not matches:
                continue

            user_msgs = [
                m
                for m in matches
                if not any(flag in m for flag in ["debug", "enqueue", "worker", "trace"])
            ]
            if user_msgs:
                print(f"\n📄 {path}")
                for msg in user_msgs:
                    intent = _infer_intent(msg)
                    print(f"  ↳ '{msg}'  → intent='{intent}'")


def _infer_intent(message: str) -> str:
    lowered = message.lower()
    for key, intent in INTENT_MAP.items():
        if key in lowered:
            return intent
    return "general"


def apply_replacement() -> None:
    for base in SEARCH_DIRS:
        for path in pathlib.Path(base).rglob("*.py"):
            original_text = path.read_text(encoding="utf-8")
            new_text = _process_file(original_text)
            if new_text != original_text:
                backup_path = path.with_suffix(path.suffix + BACKUP_SUFFIX)
                backup_path.write_text(original_text, encoding="utf-8")
                path.write_text(new_text, encoding="utf-8")
                print(f"✅ Updated {path}, backup saved to {backup_path}")


def _process_file(text: str) -> str:
    updated_text = text
    for key, intent in INTENT_MAP.items():
        pattern = re.compile(rf'send_message\(["\']([^"\']*{re.escape(key)}[^"\']*)["\']\)')
        updated_text = pattern.sub(
            _replacement_snippet(intent), updated_text
        )

    if updated_text != text and IMPORT_LINE not in updated_text:
        updated_text = _insert_import(updated_text)
    return updated_text


def _replacement_snippet(intent: str) -> str:
    return (
        f"{IMPORT_LINE}\n"
        f"reply = await compose_response(person_id, intent=\"{intent}\")\n"
        f"send_message(reply)"
    )


def _insert_import(text: str) -> str:
    lines = text.splitlines()
    insert_idx = 0
    for idx, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            insert_idx = idx + 1
        else:
            break
    lines.insert(insert_idx, IMPORT_LINE)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe send_message() migration helper.")
    parser.add_argument("--preview", action="store_true", help="Only preview matches.")
    args = parser.parse_args()

    if args.preview:
        tag_and_preview()
    else:
        apply_replacement()


if __name__ == "__main__":
    main()

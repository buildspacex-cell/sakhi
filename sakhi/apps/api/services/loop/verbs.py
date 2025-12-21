from __future__ import annotations

from typing import List

from sakhi.libs.schemas.db import get_async_pool

from ..act import calendar_dao, journal_dao, lists_dao, tasks_dao


async def dispatch_actions(user_id: str, actions: list[dict]) -> list[str]:
    confirmations: list[str] = []
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        for action in actions:
            action_type = action.get("type")

            if action_type == "plan_project":
                project_id = await tasks_dao.ensure_project(conn, user_id, action["project_name"])
                for milestone in action.get("milestones", []):
                    await tasks_dao.create_task(conn, user_id, project_id, milestone["title"])
                confirmations.append(f"Planned project '{action['project_name']}'.")

            elif action_type == "create_task":
                project_id = await tasks_dao.ensure_project(conn, user_id, action.get("project") or "Inbox")
                await tasks_dao.create_task(
                    conn,
                    user_id,
                    project_id,
                    action["title"],
                    action.get("due"),
                    action.get("notes"),
                    action.get("parent_task_id"),
                )
                confirmations.append(f"Added task '{action['title']}'.")

            elif action_type == "update_task":
                await tasks_dao.update_task_status(conn, user_id, action["task_id"], action.get("status", "todo"))
                confirmations.append("Updated task.")

            elif action_type == "add_dependency":
                await tasks_dao.add_dependency(
                    conn,
                    user_id,
                    action["task_id"],
                    action["depends_on_task_id"],
                    action.get("hard", False),
                )
                confirmations.append("Added dependency.")

            elif action_type == "remove_dependency":
                await tasks_dao.remove_dependency(
                    conn,
                    user_id,
                    action["task_id"],
                    action["depends_on_task_id"],
                )
                confirmations.append("Removed dependency.")

            elif action_type == "create_event":
                await calendar_dao.create_event(
                    user_id,
                    {
                        "title": action["title"],
                        "start": action["start"],
                        "duration_min": action.get("duration_min", 60),
                        "location": action.get("location"),
                        "notes": action.get("notes"),
                        "reminders_min_before": action.get("reminders_min_before"),
                        "link_task_id": action.get("link_task_id"),
                    },
                )
                confirmations.append(f"Scheduled '{action['title']}'.")

            elif action_type == "update_event":
                await calendar_dao.update_event_meta(
                    user_id,
                    action["event_id"],
                    {"reminders_min_before": action.get("reminders_min_before", [])},
                )
                confirmations.append("Updated event.")

            elif action_type == "add_list_item":
                await lists_dao.add_items(user_id, action["list_name"], action["items"])
                confirmations.append(f"Added {len(action['items'])} item(s) to {action['list_name']}.")

            elif action_type == "log_journal":
                await journal_dao.add_entry(
                    user_id,
                    action.get("title"),
                    action["content"],
                    action.get("tags", []),
                )
                confirmations.append("Saved your reflection.")

            elif action_type == "summarize_reflection":
                await journal_dao.add_entry(
                    user_id,
                    "Reflection",
                    "(summary)",
                    action.get("tags", []),
                )
                confirmations.append("Noted your insight.")

            else:
                confirmations.append(f"Queued {action_type}.")

    return confirmations

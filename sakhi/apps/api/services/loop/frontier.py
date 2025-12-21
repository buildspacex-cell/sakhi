from __future__ import annotations


def compute_frontier(tasks: list, deps: list):
    by_id = {task["id"]: task for task in tasks}
    edges = {}
    for edge in deps:
        edges.setdefault(edge["task_id"], []).append(edge)

    eligible = []
    for task in tasks:
        if task.get("status") not in {"todo", "in_progress", "deferred"}:
            continue

        hard_ok, soft_ok = True, True
        for edge in edges.get(task["id"], []):
            dep = by_id.get(edge["depends_on_task_id"])
            if not dep:
                continue
            if edge.get("hard") and dep.get("status") != "done":
                hard_ok = False
            if not edge.get("hard") and dep.get("status") not in {"done", "skipped"}:
                soft_ok = False

        if hard_ok and soft_ok:
            eligible.append(task)

    return eligible

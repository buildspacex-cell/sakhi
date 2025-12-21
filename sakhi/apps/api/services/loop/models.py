from __future__ import annotations

from typing import List, Optional, Literal, Union

from pydantic import BaseModel

# Finite verbs (actions)
ActionType = Literal[
    "create_task",
    "update_task",
    "complete_task",
    "skip_task",
    "defer_task",
    "add_dependency",
    "remove_dependency",
    "split_task",
    "merge_tasks",
    "create_event",
    "update_event",
    "set_reminder",
    "add_list_item",
    "plan_project",
]


class CreateTask(BaseModel):
    type: Literal["create_task"] = "create_task"
    title: str
    project: Optional[str] = None
    due: Optional[str] = None
    notes: Optional[str] = None
    parent_task_id: Optional[str] = None


class UpdateTask(BaseModel):
    type: Literal["update_task"] = "update_task"
    task_id: str
    title: Optional[str] = None
    status: Optional[Literal["todo", "in_progress", "done", "skipped", "blocked", "deferred"]] = None
    priority: Optional[int] = None
    due: Optional[str] = None
    notes: Optional[str] = None


class CompleteTask(BaseModel):
    type: Literal["complete_task"] = "complete_task"
    task_id: str


class SkipTask(BaseModel):
    type: Literal["skip_task"] = "skip_task"
    task_id: str


class DeferTask(BaseModel):
    type: Literal["defer_task"] = "defer_task"
    task_id: str
    until: Optional[str] = None


class AddDependency(BaseModel):
    type: Literal["add_dependency"] = "add_dependency"
    task_id: str
    depends_on_task_id: str
    hard: bool = False


class RemoveDependency(BaseModel):
    type: Literal["remove_dependency"] = "remove_dependency"
    task_id: str
    depends_on_task_id: str


class CreateEvent(BaseModel):
    type: Literal["create_event"] = "create_event"
    title: str
    start: str  # ISO datetime
    duration_min: int
    location: Optional[str] = None
    notes: Optional[str] = None
    reminders_min_before: Optional[List[int]] = None
    link_task_id: Optional[str] = None


class UpdateEvent(BaseModel):
    type: Literal["update_event"] = "update_event"
    event_id: str
    reminders_min_before: Optional[List[int]] = None


class SetReminder(BaseModel):
    type: Literal["set_reminder"] = "set_reminder"
    title: str
    time: str


class AddListItem(BaseModel):
    type: Literal["add_list_item"] = "add_list_item"
    list_name: str
    items: List[str]


class PlanProject(BaseModel):
    type: Literal["plan_project"] = "plan_project"
    project_name: str
    timeframe: Optional[str] = None
    milestones: List[dict] = []


class LogJournal(BaseModel):
    type: Literal["log_journal"] = "log_journal"
    title: Optional[str] = None
    content: str


class SummarizeReflection(BaseModel):
    type: Literal["summarize_reflection"] = "summarize_reflection"
    tags: List[str] = []


Action = Union[
    CreateTask,
    UpdateTask,
    CompleteTask,
    SkipTask,
    DeferTask,
    AddDependency,
    RemoveDependency,
    CreateEvent,
    UpdateEvent,
    SetReminder,
    AddListItem,
    PlanProject,
    LogJournal,
    SummarizeReflection,
]

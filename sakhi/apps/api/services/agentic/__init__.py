"""
Sakhi Agentic Service
---------------------
Enables Sakhi to act in the world on behalf of the user.

Capabilities:
- Web search and research
- Task planning and multi-step execution
- Tool invocation with user approval
- Result caching and learning
"""

from sakhi.apps.api.services.agentic.search import (
    web_search,
    news_search,
    fetch_url,
    SearchResult,
)

from sakhi.apps.api.services.agentic.tools import (
    get_available_tools,
    execute_tool,
    get_tool_by_name,
    ToolDefinition,
    ToolResult,
)

from sakhi.apps.api.services.agentic.planner import (
    create_task_plan,
    execute_task_plan,
    get_task_plan,
    approve_task_plan,
    cancel_task_plan,
    TaskPlan,
    TaskStep,
)

from sakhi.apps.api.services.agentic.research import (
    start_research,
    add_research_source,
    synthesize_research,
    ResearchSession,
)

from sakhi.apps.api.services.agentic.recurring import (
    create_recurring_schedule,
    get_recurring_schedule,
    list_recurring_schedules,
    get_recurring_schedule_runs,
    approve_recurring_schedule,
    cancel_recurring_schedule,
    run_recurring_schedule_now,
    execute_due_recurring_schedules,
    RecurringSchedule,
    RecurringRunLog,
)

__all__ = [
    # Search
    "web_search",
    "news_search",
    "fetch_url",
    "SearchResult",
    # Tools
    "get_available_tools",
    "execute_tool",
    "get_tool_by_name",
    "ToolDefinition",
    "ToolResult",
    # Planner
    "create_task_plan",
    "execute_task_plan",
    "get_task_plan",
    "approve_task_plan",
    "cancel_task_plan",
    "TaskPlan",
    "TaskStep",
    # Recurring
    "create_recurring_schedule",
    "get_recurring_schedule",
    "list_recurring_schedules",
    "get_recurring_schedule_runs",
    "approve_recurring_schedule",
    "cancel_recurring_schedule",
    "run_recurring_schedule_now",
    "execute_due_recurring_schedules",
    "RecurringSchedule",
    "RecurringRunLog",
    # Research
    "start_research",
    "add_research_source",
    "synthesize_research",
    "ResearchSession",
]

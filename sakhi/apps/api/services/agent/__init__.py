"""
Agent Services
--------------
Protocol and services for desktop/mobile agent communication.

Sakhi uses local agents to control user devices:
- Desktop agents (macOS, Windows, Linux)
- Mobile agents (iOS, Android)
- Browser extensions

The agent is "dumb hands" - it captures screen and executes actions.
The API is "smart brain" - it understands and plans.

Vision Loop Architecture:
1. Agent captures screenshot → sends to API
2. screen_analyzer.py → Claude Vision analyzes what's visible
3. action_decider.py → Claude decides next action
4. vision_loop.py → orchestrates the loop until task complete
5. Agent executes action → captures new screenshot → repeat
"""

from sakhi.apps.api.services.agent.protocol import (
    AgentCapability,
    ActionType,
    ActionStatus,
    SessionStatus,
    AgentRegistration,
    AgentHeartbeat,
    AgentAction,
    ActionResult,
    ScreenCapture,
    ScreenUnderstanding,
    AgentCommand,
    AgentResponse,
    UpdateCheck,
    UpdateInfo,
)

from sakhi.apps.api.services.agent.sessions import (
    register_agent,
    get_agent,
    update_agent_heartbeat,
    create_session,
    get_active_session,
    end_session,
)

from sakhi.apps.api.services.agent.actions import (
    queue_action,
    get_pending_actions,
    mark_action_sent,
    mark_action_completed,
    mark_action_failed,
)

from sakhi.apps.api.services.agent.vision_loop import (
    LoopStatus,
    VisionLoopState,
    StepResult,
    VisionLoop,
    start_vision_loop,
    run_vision_task,
)

from sakhi.apps.api.services.agent.screen_analyzer import (
    analyze_screen,
    analyze_screen_for_element,
    extract_text_from_screen,
    detect_page_type,
)

from sakhi.apps.api.services.agent.action_decider import (
    decide_next_action,
    decide_with_preferences,
    should_stop,
    decide_restaurant_action,
    evaluate_restaurant_option,
)

from sakhi.apps.api.services.agent.task_orchestrator import (
    TaskType,
    TaskStep,
    TaskPlan,
    TaskStatus,
    TaskResult,
    TaskOrchestrator,
    execute_task,
    execute_shopping_task,
    execute_restaurant_task,
    get_task_plan,
)

from sakhi.apps.api.services.agent.action_approval import (
    ActionRisk,
    ApprovalStatus,
    ApprovalRequest,
    ApprovalResponse,
    classify_action_risk,
    requires_approval,
    ApprovalManager,
    get_approval_manager,
    request_action_approval,
    submit_approval_response,
    get_pending_user_approvals,
)

from sakhi.apps.api.services.agent.chat_bridge import (
    AgentTaskType,
    PendingTask,
    MockExecutionState,
    detect_agent_task_intent,
    detect_task_confirmation,
    create_pending_task,
    get_pending_task,
    confirm_task,
    reject_task,
    generate_task_plan,
    start_mock_execution,
    get_mock_execution_state,
    approve_mock_step,
    format_task_plan_for_chat,
    format_execution_update_for_chat,
)

__all__ = [
    # Protocol
    "AgentCapability",
    "ActionType",
    "ActionStatus",
    "SessionStatus",
    "AgentRegistration",
    "AgentHeartbeat",
    "AgentAction",
    "ActionResult",
    "ScreenCapture",
    "ScreenUnderstanding",
    "AgentCommand",
    "AgentResponse",
    "UpdateCheck",
    "UpdateInfo",
    # Sessions
    "register_agent",
    "get_agent",
    "update_agent_heartbeat",
    "create_session",
    "get_active_session",
    "end_session",
    # Actions
    "queue_action",
    "get_pending_actions",
    "mark_action_sent",
    "mark_action_completed",
    "mark_action_failed",
    # Vision Loop
    "LoopStatus",
    "VisionLoopState",
    "StepResult",
    "VisionLoop",
    "start_vision_loop",
    "run_vision_task",
    # Screen Analysis
    "analyze_screen",
    "analyze_screen_for_element",
    "extract_text_from_screen",
    "detect_page_type",
    # Action Decision
    "decide_next_action",
    "decide_with_preferences",
    "should_stop",
    "decide_restaurant_action",
    "evaluate_restaurant_option",
    # Task Orchestrator
    "TaskType",
    "TaskStep",
    "TaskPlan",
    "TaskStatus",
    "TaskResult",
    "TaskOrchestrator",
    "execute_task",
    "execute_shopping_task",
    "execute_restaurant_task",
    "get_task_plan",
    # Action Approval
    "ActionRisk",
    "ApprovalStatus",
    "ApprovalRequest",
    "ApprovalResponse",
    "classify_action_risk",
    "requires_approval",
    "ApprovalManager",
    "get_approval_manager",
    "request_action_approval",
    "submit_approval_response",
    "get_pending_user_approvals",
    # Chat Bridge
    "AgentTaskType",
    "PendingTask",
    "MockExecutionState",
    "detect_agent_task_intent",
    "detect_task_confirmation",
    "create_pending_task",
    "get_pending_task",
    "confirm_task",
    "reject_task",
    "generate_task_plan",
    "start_mock_execution",
    "get_mock_execution_state",
    "approve_mock_step",
    "format_task_plan_for_chat",
    "format_execution_update_for_chat",
]

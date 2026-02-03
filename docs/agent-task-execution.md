# Sakhi Agent Task Execution Architecture

> Reference documentation for the agent task execution system, benchmarked against OpenClaw.

## Overview

Sakhi's task execution system enables autonomous computer control through a vision-based loop. The system captures screenshots, analyzes them with LLM vision, decides on actions, and executes them via a desktop agent.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Task Orchestrator                         │
│                    (Plan → Confirm → Execute)                    │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Vision Loop                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Capture  │ → │ Analyze  │ → │  Decide  │ → │ Execute  │   │
│  │Screenshot│    │  Screen  │    │  Action  │    │  Action  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       ▲                                               │         │
│       └───────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Desktop Agent                              │
│              (Electron app with RobotJS)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `sakhi/apps/api/services/agent/vision_loop.py` | Core execution loop |
| `sakhi/apps/api/services/agent/screen_analyzer.py` | LLM vision analysis |
| `sakhi/apps/api/services/agent/action_decider.py` | Action decision logic |
| `sakhi/apps/api/services/agent/actions.py` | Action queue & commands |
| `sakhi/apps/api/services/agent/sessions.py` | Session management |
| `sakhi/apps/api/services/agent/errors.py` | Error classification |
| `sakhi/apps/api/services/agent/timeouts.py` | Timeout utilities |
| `sakhi/apps/api/services/agent/session_lock.py` | Concurrency control |
| `sakhi/apps/api/services/agent/task_orchestrator.py` | High-level task planning |
| `sakhi/apps/desktop-agent/src/main/agent.ts` | Desktop agent (Electron) |

---

## Production Features

### 1. Error Classification

Based on OpenClaw's `FailoverError` pattern. Errors are explicitly classified for intelligent retry decisions.

```python
from sakhi.apps.api.services.agent.errors import (
    AgentError,
    ErrorReason,
    classify_error,
    is_retryable_error,
)

# Error reasons
class ErrorReason(Enum):
    AUTH = "auth"              # 401 - Authentication failed
    RATE_LIMIT = "rate_limit"  # 429 - API rate limited
    BILLING = "billing"        # 402 - Quota exceeded
    TIMEOUT = "timeout"        # 504 - Request timed out
    CONTEXT_OVERFLOW = "context_overflow"  # 413 - Token limit
    NETWORK = "network"        # 503 - Network issue
    AGENT_OFFLINE = "agent_offline"  # 503 - Desktop agent down
    SESSION_LOCKED = "session_locked"  # 423 - Concurrent access
    UNKNOWN = "unknown"        # 500 - Unclassified

# Usage
try:
    await some_operation()
except Exception as e:
    classified = classify_error(e, context={"session_id": "..."})
    if classified.is_retryable():
        delay_ms = get_retry_delay_ms(classified, attempt=1)
        await asyncio.sleep(delay_ms / 1000)
```

### 2. Retry Logic with Exponential Backoff

Multi-layer retry similar to OpenClaw's 5-layer recovery.

```python
# Retry configuration in VisionLoopState
max_retries_per_step: int = 3      # Retries per step
consecutive_errors: int = 0         # Track consecutive failures
total_retries: int = 0              # Total retries in session

# Backoff calculation
def get_retry_delay_ms(error: Exception, attempt: int) -> int:
    """
    Exponential backoff: base * 2^(attempt-1), capped at 60s
    """
    base_delay = 5000  # 5 seconds
    delay = base_delay * (2 ** (attempt - 1))
    return min(delay, 60000)  # Max 1 minute
```

### 3. Timeout Management

Defensive timeouts with min/max clamping to prevent both premature failures and indefinite hangs.

```python
from sakhi.apps.api.services.agent.timeouts import (
    Timeouts,
    clamp_timeout,
    with_timeout,
)

# Predefined timeouts (milliseconds)
class Timeouts:
    GLOBAL_MIN_MS = 500
    GLOBAL_MAX_MS = 600_000  # 10 minutes

    ACTION_EXECUTION = 8_000
    SCREEN_ANALYSIS = 30_000
    ACTION_DECISION = 15_000
    SCREENSHOT_WAIT = 60_000
    LOCK_ACQUISITION = 10_000
    SESSION_TIMEOUT = 1_800_000  # 30 minutes

# Usage
timeout = clamp_timeout(
    user_timeout,
    default_ms=8000,
    min_ms=500,
    max_ms=60000,
)

result = await with_timeout(
    some_operation(),
    timeout_ms=30000,
    operation_name="screen_analysis",
)
```

### 4. Session Write Locking

PostgreSQL advisory locks prevent concurrent writes to the same session.

```python
from sakhi.apps.api.services.agent.session_lock import (
    session_write_lock,
    acquire_session_lock,
    release_session_lock,
)

# Context manager (recommended)
async with session_write_lock(session_id, timeout_ms=10000):
    await update_session_state(...)

# Manual control
lock = await acquire_session_lock(session_id)
try:
    await update_session_state(...)
finally:
    await release_session_lock(lock)
```

**Features:**
- PostgreSQL advisory locks (production-grade)
- In-memory fallback (for testing/no-DB scenarios)
- Stale lock detection (30 min timeout)
- Exponential backoff on contention

### 5. Thread-Safe Command Queue

Commands are delivered to desktop agents via heartbeat responses.

```python
from sakhi.apps.api.services.agent.actions import (
    queue_agent_command,
    get_pending_commands,
)

# Queue a command
cmd_id = await queue_agent_command(
    agent_id="agent-123",
    command="start_session",
    parameters={
        "session_id": "session-456",
        "task_description": "Book a restaurant",
    },
)

# Agent retrieves on heartbeat (in sessions.py)
commands = await get_pending_commands(agent_id)
```

**Features:**
- `asyncio.Lock` for thread safety
- Optional DB persistence (`PERSIST_AGENT_COMMANDS=true`)
- Stale command cleanup
- Queue diagnostics

### 6. Action History with Compaction

Full action history maintained for LLM context, with automatic compaction.

```python
# In VisionLoopState
action_history: List[Dict[str, Any]] = []

# Compaction (50 items max)
MAX_HISTORY = 50
if len(action_history) > MAX_HISTORY:
    # Keep first 5 (initial context) + last 45 (recent)
    action_history = action_history[:5] + action_history[-45:]
```

---

## Vision Loop Execution Flow

```python
async def start(self, task_description: str) -> VisionLoopState:
    # 1. Initialize state
    self.state = VisionLoopState(...)

    # 2. Notify desktop agent
    await self._notify_agent_session_start(task_description)

    # 3. Wait for initial screenshot
    screenshot = await self._wait_for_screenshot(timeout_seconds=60)
    if not screenshot:
        # Agent not responding
        return self.state

    # 4. Main loop with retry
    while self._should_continue():
        step_retry_count = 0

        while step_retry_count <= max_retries:
            try:
                result = await self._execute_step_with_timeout()

                # Success - clear error tracking
                self.state.consecutive_errors = 0

                if result.is_complete:
                    self.state.status = LoopStatus.COMPLETED
                    break

            except AgentError as e:
                if e.is_retryable():
                    step_retry_count += 1
                    delay = get_retry_delay_ms(e, step_retry_count)
                    await asyncio.sleep(delay / 1000)
                    continue
                break
```

---

## Desktop Agent Integration

### Heartbeat Flow

```
Desktop Agent                    API Server
     │                               │
     │──── POST /agent/heartbeat ───▶│
     │     {status: "online"}        │
     │                               │
     │◀─── HeartbeatResponse ────────│
     │     {commands: [...]}         │
     │                               │
     │     (Execute command)         │
     │                               │
     │──── POST /agent/screenshot ──▶│
     │     {image_base64: "..."}     │
     │                               │
```

### Session Start Command

```typescript
// Desktop agent receives via heartbeat
case 'start_session':
    const existingSessionId = cmd.parameters.session_id
    if (existingSessionId) {
        // Join existing session (VisionLoop created it)
        this.updateState({
            status: 'active',
            sessionId: existingSessionId,
            currentTask: cmd.parameters.task_description,
        })
        await this.captureAndSubmitScreen('session_start')
    }
    break
```

---

## Comparison with OpenClaw

| Feature | OpenClaw | Sakhi | Status |
|---------|----------|-------|--------|
| Error Classification | FailoverError | AgentError | ✅ At par |
| Retry Logic | 5-layer | 3-layer | ✅ Functional |
| Timeout Clamping | min/max bounds | Timeouts class | ✅ At par |
| Session Locking | File-based | PostgreSQL advisory | ✅ Better |
| Command Queue | Lane-based | asyncio.Lock + DB | ✅ At par |
| Action History | Full + compact | 50-item compact | ✅ At par |
| State Persistence | JSON files | PostgreSQL | ✅ Better |
| Auth Rotation | Multi-profile | Single profile | ⚠️ Not needed |
| Browser Control | Playwright | Screenshot + Vision | 🔄 Different |

### Browser Automation Approaches

**OpenClaw (Playwright):**
- Direct DOM manipulation
- CSS selector targeting
- Fast (~100-500ms/action)
- Web-only

**Sakhi (Vision):**
- Screenshot + LLM analysis
- Coordinate-based clicking
- Slower (~2-5s/action)
- Works with any application (web + native)

---

## Configuration

### Environment Variables

```bash
# LLM Configuration
MODEL_CHAT=gpt-4o-mini
MODEL_EMBED=text-embedding-3-small

# Agent Configuration
PERSIST_AGENT_COMMANDS=false  # Enable DB persistence for commands
USE_DB_SESSION_LOCKS=true     # Use PostgreSQL advisory locks
```

### Timeout Tuning

Modify `sakhi/apps/api/services/agent/timeouts.py`:

```python
class Timeouts:
    ACTION_EXECUTION = 8_000      # Per-action timeout
    SCREEN_ANALYSIS = 30_000      # Vision LLM call
    SESSION_TIMEOUT = 1_800_000   # 30 min session limit
```

---

## Error Handling Best Practices

1. **Always classify errors** before deciding retry:
   ```python
   classified = classify_error(e)
   if classified.is_retryable():
       # Retry with backoff
   ```

2. **Track consecutive errors** to detect stuck loops:
   ```python
   if consecutive_errors >= 5:
       # Stop execution
   ```

3. **Use session locks** for any state mutation:
   ```python
   async with session_write_lock(session_id):
       await update_state(...)
   ```

4. **Clamp all timeouts** to prevent extremes:
   ```python
   timeout = clamp_timeout(user_value, default=8000, min=500, max=60000)
   ```

---

## Future Enhancements

1. **Context Window Compaction** - Compress full session history on overflow
2. **Auth Profile Rotation** - Multiple API keys with cooldown tracking
3. **Playwright Fallback** - Use direct DOM control for web tasks when faster
4. **Skill/Plugin System** - Dynamic capability loading

---

## References

- OpenClaw source: `/Users/fanantics/Downloads/openclaw-main/`
- Key OpenClaw files:
  - `src/agents/pi-embedded-runner/run.ts` - Main execution loop
  - `src/agents/failover-error.ts` - Error classification
  - `src/agents/session-write-lock.ts` - Locking
  - `src/browser/pw-session.ts` - Playwright integration

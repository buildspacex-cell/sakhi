# Agent Task Orchestrator

> **Sakhi's autonomous task execution system** — Preference-aware, multi-hop reasoning that browses the web on your behalf.

---

## Overview

The Task Orchestrator is Sakhi's "planner + executor" that enables intelligent autonomous task execution. Unlike simple automation, it:

1. **Knows you** — Pulls your preferences, memories, and constraints before acting
2. **Plans intelligently** — Decomposes tasks into multi-step plans using Claude
3. **Executes autonomously** — Runs a vision loop that sees, decides, and acts
4. **Adapts to you** — Every decision considers your sensory preferences and history

```
┌─────────────────────────────────────────────────────────────────┐
│  "Find me running shoes on Amazon"                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  1. GATHER CONTEXT                                               │
│     → Recall: "knee pain", "run 3x/week", "likes Nike"          │
│     → Preferences: firm support, breathable (hot areas)         │
│     → Constraints: under $150, avoid narrow fit                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. PLAN TASK                                                    │
│     → Step 1: Navigate to Amazon                                │
│     → Step 2: Search "running shoes cushioned support"          │
│     → Step 3: Filter by price, customer rating                  │
│     → Step 4: Compare top 3 options                             │
│     → Step 5: Select best match for user                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. EXECUTE (Vision Loop)                                        │
│     Screenshot → Claude Vision → Decide → Act → Repeat          │
│     Each decision informed by preferences                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Result: "Nike Air Zoom Pegasus 41 - $129"                      │
│  Why: Cushioned, breathable, great for knee issues              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **Task Orchestrator** | `services/agent/task_orchestrator.py` | Main coordinator - connects preferences, memory, planning, execution |
| **Vision Loop** | `services/agent/vision_loop.py` | Screenshot → Analyze → Decide → Act cycle |
| **Screen Analyzer** | `services/agent/screen_analyzer.py` | Claude Vision analysis of screenshots |
| **Action Decider** | `services/agent/action_decider.py` | Decides next action based on screen + context |
| **Sensory Preferences** | `services/memory/sensory_preferences.py` | User's sensory preferences (temperature, texture, etc.) |
| **Food Memory** | `services/memory/food_memory.py` | Food experiences, restaurant history |
| **Hybrid Search** | `services/memory/recall.py` + `bm25.py` | Memory recall via BM25 + vector search |

### Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                     TASK ORCHESTRATOR                        │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │   Sensory    │   │    Food      │   │   Hybrid     │    │
│  │ Preferences  │   │   Memory     │   │   Search     │    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘    │
│         │                  │                  │             │
│         └────────────┬─────┴──────────────────┘             │
│                      ↓                                       │
│              ┌───────────────┐                               │
│              │    CONTEXT    │                               │
│              │  preferences  │                               │
│              │   memories    │                               │
│              │  constraints  │                               │
│              └───────┬───────┘                               │
│                      ↓                                       │
│              ┌───────────────┐                               │
│              │   PLANNER     │ ← Claude creates multi-step   │
│              │               │   plan from context           │
│              └───────┬───────┘                               │
│                      ↓                                       │
│              ┌───────────────┐                               │
│              │ VISION LOOP   │                               │
│              │               │                               │
│              │  Screenshot   │                               │
│              │      ↓        │                               │
│              │  Analyze      │ ← Claude Vision               │
│              │      ↓        │                               │
│              │  Decide       │ ← Context-aware               │
│              │      ↓        │                               │
│              │  Execute      │                               │
│              │      ↓        │                               │
│              │  (repeat)     │                               │
│              └───────────────┘                               │
└──────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Execute Task (General)

```http
POST /api/v1/agent/task/execute
```

Execute any preference-aware autonomous task.

**Request:**
```json
{
  "task_description": "Find me the best noise-canceling headphones under $300",
  "agent_id": "your-agent-id",
  "starting_url": "https://amazon.com",
  "context": {}
}
```

**Response:**
```json
{
  "task_id": "a1b2c3d4",
  "status": "completed",
  "steps_completed": 5,
  "total_steps": 5,
  "plan_summary": "User prefers quiet environments, works from home. Looking for comfort over portability.",
  "constraints_applied": [
    "Budget: under $300",
    "User has sensitive ears - prefer soft ear cushions",
    "Previous purchase: Sony WH-1000XM3 (liked)"
  ],
  "results": {
    "step_1": { "status": "completed", "actions_taken": 2 },
    "step_2": { "status": "completed", "actions_taken": 4 },
    ...
  },
  "context_used": {
    "memories_recalled": 3,
    "has_preferences": true,
    "constraints": ["Budget: under $300", ...]
  }
}
```

---

### Shopping Task

```http
POST /api/v1/agent/task/shopping
```

Specialized endpoint for shopping tasks.

**Request:**
```json
{
  "product_query": "running shoes for marathon training",
  "agent_id": "your-agent-id",
  "site": "amazon",
  "max_price": 150.00
}
```

**Response:**
```json
{
  "task_id": "b2c3d4e5",
  "status": "completed",
  "product_query": "running shoes for marathon training",
  "site": "amazon",
  "max_price": 150.00,
  "steps_completed": 5,
  "results": { ... },
  "errors": []
}
```

**Supported sites:**
- `amazon` (default)
- `ebay`
- `walmart`
- `target`

---

### Restaurant Task

```http
POST /api/v1/agent/task/restaurant
```

Find restaurants considering your dining preferences and food history.

**Request:**
```json
{
  "agent_id": "your-agent-id",
  "cuisine": "Italian",
  "location": "San Francisco",
  "party_size": 2,
  "date": "tonight",
  "price_range": "moderate"
}
```

**Response:**
```json
{
  "task_id": "c3d4e5f6",
  "status": "completed",
  "search_criteria": {
    "cuisine": "Italian",
    "location": "San Francisco",
    "party_size": 2,
    "date": "tonight",
    "price_range": "moderate"
  },
  "steps_completed": 4,
  "results": { ... },
  "food_context_used": true,
  "errors": []
}
```

**What gets considered:**
- Your sensory preferences (spice tolerance, temperature, ambiance)
- Recent meals (to avoid repetition)
- Restaurant history (favorite places)
- Dietary restrictions and allergies

---

### Preview Plan (No Execution)

```http
POST /api/v1/agent/task/plan
```

Preview what Sakhi would do without executing.

**Request:**
```json
{
  "task_description": "Order groceries for the week"
}
```

**Response:**
```json
{
  "task_type": "shopping",
  "original_request": "Order groceries for the week",
  "steps": [
    {
      "step_number": 1,
      "action": "navigate",
      "description": "Open grocery delivery service",
      "success_criteria": "Grocery site loaded",
      "estimated_actions": 2
    },
    {
      "step_number": 2,
      "action": "search",
      "description": "Search for weekly staples based on user's food preferences",
      "success_criteria": "Search results displayed",
      "estimated_actions": 3
    },
    ...
  ],
  "total_estimated_actions": 15,
  "context_summary": "User prefers organic produce, is vegetarian, and typically shops for 2 people",
  "constraints": [
    "Vegetarian diet",
    "Prefer organic when available",
    "Recently bought: milk, bread (don't duplicate)"
  ],
  "success_criteria": "Groceries in cart, ready for checkout"
}
```

---

## Task Types

The orchestrator automatically classifies tasks:

| Type | Triggered By | Starting URL |
|------|--------------|--------------|
| `shopping` | "buy", "purchase", "order", "shop", "amazon", "find product" | Site-specific |
| `food` | "restaurant", "food", "eat", "dinner", "lunch", "dine" | Google Maps |
| `booking` | "book", "reserve", "reservation", "appointment" | Context-specific |
| `research` | "research", "find out", "learn about", "what is" | Google |
| `browsing` | Default fallback | Provided URL or Google |

---

## Context Gathering

Before planning, the orchestrator gathers:

### 1. Sensory Preferences

```python
from sakhi.apps.api.services.memory.sensory_preferences import get_sensory_profile

profile = await get_sensory_profile(person_id)
# Returns: temperature_preference, texture_preference, spice_tolerance, ambiance_preference
```

### 2. Food Memory (if relevant)

```python
from sakhi.apps.api.services.memory.food_memory import (
    get_food_context_for_recommendations,
    get_recent_meals,
)

context = await get_food_context_for_recommendations(person_id)
recent = await get_recent_meals(person_id, days=3)
```

### 3. Relevant Memories (Hybrid Search)

```python
from sakhi.apps.api.services.memory.recall import recall_advanced

memories = await recall_advanced(
    person_id=person_id,
    query=task_description,
    k=10,  # Top 10 results
)
# Uses BM25 (keyword) + Vector (semantic) with 0.7/0.3 weighting
```

### 4. Extracted Constraints

The orchestrator extracts actionable constraints from context:

- `"User has low spice tolerance"` (from sensory preferences)
- `"Allergies: peanuts, shellfish"` (from food context)
- `"Recently ate: pizza, sushi"` (to avoid repetition)
- `"May not like: crowded places"` (from memories)

---

## Vision Loop

The vision loop is the execution engine:

```python
from sakhi.apps.api.services.agent.vision_loop import VisionLoop

loop = VisionLoop(
    session_id="...",
    agent_id="...",
    person_id="...",
    max_steps=50,          # Safety limit
    step_delay_ms=500,     # Delay between steps
    timeout_minutes=30,    # Max execution time
)

state = await loop.start(
    task_description="Search for running shoes",
    initial_context={"preferences": {...}, "constraints": [...]},
    starting_url="https://amazon.com",
)
```

### Loop States

| State | Description |
|-------|-------------|
| `idle` | Not started |
| `running` | Actively executing |
| `paused` | Temporarily paused |
| `waiting_input` | Waiting for user input |
| `completed` | Task finished successfully |
| `failed` | Task failed (errors or timeout) |
| `cancelled` | User cancelled |

### Actions

The vision loop can perform:

| Action | Parameters | Example |
|--------|------------|---------|
| `click` | `{x, y}` | Click on "Add to Cart" button |
| `type` | `{text}` | Type search query |
| `key` | `{key}` | Press Enter, Tab, Escape |
| `scroll` | `{direction, amount}` | Scroll down to see more results |
| `navigate` | `{url}` | Go to a specific URL |
| `wait` | `{ms}` | Wait for page to load |

---

## Usage Examples

### Python (Direct)

```python
from sakhi.apps.api.services.agent.task_orchestrator import (
    execute_task,
    execute_shopping_task,
    execute_restaurant_task,
    get_task_plan,
)

# General task
result = await execute_task(
    person_id="user-123",
    agent_id="agent-456",
    task_description="Find me a birthday gift for Mom under $50",
)

# Shopping task
result = await execute_shopping_task(
    person_id="user-123",
    agent_id="agent-456",
    product_query="wireless earbuds with good bass",
    site="amazon",
    max_price=100.00,
)

# Restaurant task
result = await execute_restaurant_task(
    person_id="user-123",
    agent_id="agent-456",
    criteria={
        "cuisine": "Japanese",
        "location": "Downtown",
        "party_size": 4,
        "price_range": "moderate",
    },
)

# Preview only
plan = await get_task_plan(
    person_id="user-123",
    task_description="Book a haircut appointment",
)
```

### cURL

```bash
# Execute shopping task
curl -X POST http://localhost:8000/api/v1/agent/task/shopping \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "product_query": "noise canceling headphones",
    "agent_id": "your-agent-id",
    "site": "amazon",
    "max_price": 200
  }'

# Preview plan
curl -X POST http://localhost:8000/api/v1/agent/task/plan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "task_description": "Find a good Italian restaurant for dinner tonight"
  }'
```

---

## Models

### TaskPlan

```python
class TaskPlan(BaseModel):
    task_id: str
    task_type: TaskType  # shopping, food, booking, research, browsing
    original_request: str
    steps: List[TaskStep]
    total_estimated_actions: int
    context_summary: str
    constraints: List[str]
    success_criteria: str
```

### TaskStep

```python
class TaskStep(BaseModel):
    step_number: int
    action: str  # navigate, search, filter, select, verify, complete
    description: str
    success_criteria: str
    fallback: Optional[str]
    depends_on: Optional[int]
    estimated_actions: int
```

### TaskResult

```python
class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    plan: Optional[TaskPlan]
    steps_completed: int
    current_step: int
    results: Dict[str, Any]  # Results per step
    errors: List[str]
    context_used: Dict[str, Any]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

---

## Integration with Existing Systems

### Hybrid Search Integration

The orchestrator uses the same hybrid search that powers conversations:

```
User Query
    ↓
recall_advanced()
    ↓
┌─────────────────────────────────────────┐
│  BM25 (Keyword)    +    Vector (Semantic) │
│      0.3 weight          0.7 weight      │
└─────────────────────────────────────────┘
    ↓
merge_hybrid_scores()
    ↓
Top K Results
```

### Sensory Preferences

Preferences learned from conversations are used in task execution:

```
Conversation: "I can't handle spicy food"
                ↓
learn_preference_from_text()
                ↓
SensoryProfile.spice_tolerance = "low"
                ↓
Restaurant Task: Filters out spicy cuisines
```

### Food Memory

Past food experiences inform restaurant recommendations:

```
Meal recorded: "Loved the pasta at Bella Italia"
                ↓
RestaurantMemory: Bella Italia → 5 stars
                ↓
Restaurant Task: "You've enjoyed Bella Italia before - they have a new seasonal menu"
```

---

## Action Approval Flow

Critical actions require explicit user confirmation before Sakhi proceeds. This ensures Sakhi never takes irreversible actions without your consent.

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Vision Loop detects: "Add to Cart" button click coming     │
│                                                             │
│  Action classified as: HIGH RISK                            │
│                                                             │
│  Loop PAUSES → Status: waiting_approval                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Chat Interface Shows:                                       │
│                                                             │
│  Sakhi: "I found Nike Air Zoom Pegasus for $129.            │
│          Should I add it to your cart?"                     │
│                                                             │
│  [Yes, add to cart]  [Show me other options]  [Cancel]      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  User approves → Loop RESUMES → Executes action             │
│  User rejects  → Loop continues with alternatives           │
└─────────────────────────────────────────────────────────────┘
```

### Risk Levels

Actions are classified into four risk levels:

| Risk Level | Examples | Approval Required |
|------------|----------|-------------------|
| **LOW** | Navigate, scroll, search, filter, view details | No |
| **MEDIUM** | Add to wishlist, save for later | Optional (user setting) |
| **HIGH** | Add to cart, book, subscribe, sign up | Yes |
| **CRITICAL** | Purchase, checkout, delete, post publicly | Always |

### Actions Requiring Approval

**HIGH Risk (requires approval):**
- `add_to_cart` - Adding items to shopping cart
- `book` / `reserve` - Making bookings/reservations
- `subscribe` - Starting subscriptions
- `sign_up` - Creating accounts
- `submit_form` - Submitting forms with data

**CRITICAL Risk (always requires approval):**
- `purchase` / `checkout` / `buy_now` - Financial transactions
- `delete` / `remove` - Permanent deletions
- `post` / `publish` - Public content creation
- `send` / `share` - Sending messages or sharing

### Approval API Endpoints

#### Get Pending Approvals

```http
GET /api/v1/agent/task/approvals/pending
```

Returns all actions waiting for user confirmation.

**Response:**
```json
{
  "pending": [
    {
      "request_id": "abc123",
      "action_type": "add_to_cart",
      "action_description": "Add Nike Air Zoom Pegasus to cart",
      "risk_level": "high",
      "context_summary": "Found shoes matching your preferences for cushioned support",
      "why_approval_needed": "This will add an item to your shopping cart",
      "if_approved": "Will add Nike Air Zoom to cart",
      "if_rejected": "Will continue with alternatives or stop",
      "options": [
        {"label": "Yes, add to cart", "value": "approve"},
        {"label": "Show me other options", "value": "alternatives"},
        {"label": "Cancel", "value": "reject"}
      ],
      "expires_in_seconds": 245
    }
  ],
  "count": 1
}
```

#### Respond to Approval

```http
POST /api/v1/agent/task/approvals/{request_id}/respond
```

**Request:**
```json
{
  "approved": true,
  "selected_option": "approve",
  "comment": "Looks good!"
}
```

**Response:**
```json
{
  "success": true,
  "request_id": "abc123",
  "status": "approved",
  "message": "Action will proceed"
}
```

### Chat Integration

The approval flow is designed to integrate naturally with the chat interface:

```typescript
// Frontend listens for approval events
const { pending } = await fetch('/api/v1/agent/task/approvals/pending');

if (pending.length > 0) {
  // Show approval prompt in chat
  showApprovalPrompt({
    message: pending[0].context_summary,
    options: pending[0].options,
    onApprove: () => respondToApproval(pending[0].request_id, true),
    onReject: () => respondToApproval(pending[0].request_id, false),
  });
}
```

### Timeout Behavior

- Approval requests expire after **5 minutes** by default
- If expired, the vision loop continues without taking the action
- User can configure timeout in settings

---

## Safety & Limits

| Limit | Default | Purpose |
|-------|---------|---------|
| `max_steps` | 50 | Prevent infinite loops |
| `max_actions_per_step` | 20 | Limit actions per plan step |
| `timeout_minutes` | 30 | Total execution time limit |
| `error_threshold` | 3 | Consecutive errors before failing |
| `approval_timeout` | 300s | Time to wait for user approval |

---

## Future Enhancements

- [x] ~~Purchase approval flow (require user confirmation before buying)~~ **DONE**
- [ ] Multi-agent coordination (your Sakhi + store's Sakhi)
- [ ] Learning from execution (improve plans based on outcomes)
- [ ] Parallel step execution (independent steps run simultaneously)
- [ ] Rollback support (undo actions if task fails midway)
- [ ] Auto-approve settings (user can pre-approve certain actions)

---

## Related Documentation

- [Vision Integration](voice.md) — Speech input for tasks
- [Adaptive Response](adaptive-response.md) — How Sakhi communicates
- [Body State](body-state.md) — Health-aware recommendations
- [System Overview](../architecture/system-overview.md) — Full architecture

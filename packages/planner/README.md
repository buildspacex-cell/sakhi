# @sakhi/planner

Rule-based response planner that encodes the five dual-objective reply patterns from the architecture doc:

1. Listen/Reflect only.
2. Reflect + single clarifying question.
3. Plan Lite (light actions, quick tasks).
4. Plan Deep (propose focus blocks).
5. Encourage + Track (nudges for habits).

## Usage

```ts
import { RuleBasedPlanner } from "@sakhi/planner";
import type { PlannerInput } from "@sakhi/planner";

const planner = new RuleBasedPlanner();
const plan = await planner.plan(input);
```

Provide `PlannerInput` with `messageId`, `context` (ContextPack), and extracted facets. The planner selects a pattern based on facets and outputs a `PlanGraph` validated via `@sakhi/contracts`.

Extend by adding new entries to `PATTERNS` or overriding `pickPattern` with ML/LLM strategies.

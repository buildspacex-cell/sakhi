# @sakhi/orchestrator

Listens for `message.ingested` events, retrieves facets, builds context packs, and produces `plan.ready` events by chaining the context builder and planner packages. It is responsible for coordinating the conversation loop across the event bus.

## Usage

```ts
import { ConversationOrchestrator } from "@sakhi/orchestrator";
import { WorkingContextBuilder } from "@sakhi/context-builder";
import { RuleBasedPlanner } from "@sakhi/planner";

const orchestrator = new ConversationOrchestrator({
  contextBuilder,
  planner,
  getFacets: async (messageId) => facetStore.fetch(messageId)
});

orchestrator.start();
```

Provide your implementations of:

- `getFacets`: fetch from the facet extractor, or run synchronous extraction here.
- `contextBuilder`: configured with memory/schedule/rhythm stores.
- `planner`: any planner implementing the `plan()` method.

Downstream services can subscribe to `plan.ready` to render replies or route actions.

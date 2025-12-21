# @sakhi/learning-engine

Subscribes to domain events and updates the Memory Service with short-term entries, episodic notes, and semantic hypotheses. This is a skeleton for future consolidation logic.

```ts
import { LearningEngine } from "@sakhi/learning-engine";
import { InMemoryMemoryService } from "@sakhi/memory-service";

const engine = new LearningEngine({ memoryService: new InMemoryMemoryService() });
engine.start();
```

Extend by handling `reply.rendered` outcomes, raising confidence scores when users confirm hypotheses, and scheduling nightly/weekly consolidation jobs.

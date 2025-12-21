# @sakhi/context-builder

Composes short-term buffer, episodic history, semantic traits, schedule slices, and rhythm signals into a `ContextPack` that downstream planners can consume. This package only depends on the contracts package so it can run in workers or serverless functions.

## Usage

```ts
import { WorkingContextBuilder } from "@sakhi/context-builder";
import { InMemoryMemoryStore } from "@sakhi/context-builder/memoryStore.mock";
import { InMemoryScheduleStore } from "@sakhi/context-builder/scheduleStore.mock";
import { StaticRhythmEngine } from "@sakhi/context-builder/rhythmEngine.mock";
import { MessageSchema } from "@sakhi/contracts";

const memory = new InMemoryMemoryStore();
const schedule = new InMemoryScheduleStore();
const rhythms = new StaticRhythmEngine();

const message = MessageSchema.parse(/*...*/);

const builder = new WorkingContextBuilder({ memoryStore: memory, scheduleStore: schedule, rhythmEngine: rhythms });
const pack = await builder.build({ userId: message.user_id, turnId: "turn-123", message, now: new Date() });
```

Implement the `MemoryStore`, `ScheduleStore`, and `RhythmEngine` interfaces in production to plug into real data sources.

## Context Recipe

The builder accepts a `recipe` to control how many working items / episodic hits to include and to specify hard/soft pins. Provide custom recipes per persona or deploy environment.

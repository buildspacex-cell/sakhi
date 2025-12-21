# @sakhi/memory-service

Backing store abstraction for the Short-Term Buffer, Episodic Store, Semantic Traits, Preferences, and Identity Graph. Ships with an in-memory implementation for local dev/tests plus a Postgres-backed implementation for persistence.

```ts
import { InMemoryMemoryService, PostgresMemoryService } from "@sakhi/memory-service";

const memory = new InMemoryMemoryService();
await memory.appendShortTerm(userId, stmRecord);
const recent = await memory.getShortTerm(userId, 10);
```

To use Postgres:

```
const memory = new PostgresMemoryService({ connectionString: process.env.MEMORY_PG_URL! });
```

In production, replace with adapters to Postgres, Redis, or vector DBs while keeping the same interface.

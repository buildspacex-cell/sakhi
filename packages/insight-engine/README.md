# @sakhi/insight-engine

Produces weekly summaries (highlights + simple mood estimate) from the memory service. This is a placeholder for the “Soul” layer used to generate reflections and rhythms.

```ts
const engine = new InsightEngine(memoryService);
const insight = await engine.synthesizeWeekly(userId, new Date('2025-01-13'));
```

Extend `summarizeHighlights` and `estimateMood` with LLM prompts or analytics jobs as the data matures.

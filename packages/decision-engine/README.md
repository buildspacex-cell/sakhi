# @sakhi/decision-engine

Encodes decision templates (wardrobe, pre-workout meal, travel pack, route, gift) so conversation flows can offer 2–3 distinctive options with a micro question, learning hints, and tiny action.

```ts
const engine = new DecisionEngine();
const result = engine.decide("wardrobe", { setting: "conference", indoor: "indoor" });
```

Extend `decide()` with additional intents (travel pack, gift, route) as templates mature.

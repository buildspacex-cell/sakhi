# @sakhi/policy-engine

Listens to `plan.ready` events, selects a tone/pacing based on plan objective, rhythms, quiet-hours, and stored preferences, and emits a `reply.rendered` event with rendered text. Plug in an `LLMRenderer` to generate responses via an LLM when `semantic_profile.preferences["tone.renderer"] === "llm"`.

```
const engine = new PolicyEngine();
engine.start();
```

Extend `selectTone` and `renderReply` with richer heuristics or LLM prompts.

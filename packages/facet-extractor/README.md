# @sakhi/facet-extractor

Contracts and reference implementations for extracting Person and Activity facets from messages.

- `FacetExtractor` interface (input/output match the spec in `docs/facet-extractor.md`).
- `SimpleFacetExtractor`: keyword + verb-based baseline useful for tests and local dev. Swap it out with LLM-backed implementations later.

```ts
import { SimpleFacetExtractor } from "@sakhi/facet-extractor";

const extractor = new SimpleFacetExtractor();
const { facets } = await extractor.extract({ message });
```

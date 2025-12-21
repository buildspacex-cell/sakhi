import type { ContextPack, Facet, PlanGraph } from "@sakhi/contracts";

export interface PlannerInput {
  messageId: string;
  context: ContextPack;
  facets: Facet[];
}

export interface PlanOutput {
  plan: PlanGraph;
  extras?: Record<string, unknown>;
}

export interface Planner {
  plan(input: PlannerInput): Promise<PlanOutput>;
}

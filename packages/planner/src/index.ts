import { PlanGraphSchema, type PlanGraph } from "@sakhi/contracts";
import type { Planner, PlannerInput } from "./types";
import { pickPattern, createPatterns } from "./patterns";
import { DecisionEngine } from "@sakhi/decision-engine";
import type { PlanOutput } from "./types";

export class RuleBasedPlanner implements Planner {
  private readonly patterns;

  constructor(private readonly decisionEngine = new DecisionEngine()) {
    this.patterns = createPatterns(this.decisionEngine);
  }

  async plan(input: PlannerInput): Promise<PlanOutput> {
    const pattern = pickPattern(this.patterns, input);
    const plan = pattern.build(input);
    const { extras, ...rest } = plan as any;
    const parsed = PlanGraphSchema.parse({
      ...rest,
      schema_version: rest.schema_version ?? "0.1.0"
    });
    return { plan: parsed, extras };
  }
}

export * from "./types";
export * from "./patterns";

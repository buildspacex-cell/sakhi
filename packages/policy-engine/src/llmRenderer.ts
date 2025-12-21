import type { PlanGraph, ContextPack } from "@sakhi/contracts";

export interface LLMRenderer {
  render(plan: PlanGraph, context: ContextPack, tone: string): Promise<string>;
}

export class StubLLMRenderer implements LLMRenderer {
  async render(plan: PlanGraph): Promise<string> {
    return plan.steps.map((step) => {
      if (step.type === "reflection") return step.text_template;
      if (step.type === "question") return step.template;
      return "";
    }).join(" ");
  }
}

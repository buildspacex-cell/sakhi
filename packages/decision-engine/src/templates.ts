import registry from "../templates/registry.json";
export type DecisionIntent = string;
export type DecisionOption = { label: string; rationale: string };
export type DecisionResult = {
  intent: DecisionIntent;
  microQuestion?: string;
  options: DecisionOption[];
  tinyAction?: string;
  learningHints?: Array<{ key: string; value: string }>;
};

export class DecisionEngine {
  private readonly templates = registry;

  decide(intent: DecisionIntent, providedSlots: Record<string, string | undefined> = {}): DecisionResult {
    const template = this.templates.find((tpl) => tpl.intent === intent);
    if (!template) {
      return { intent, options: [], microQuestion: "Tell me more about what you need" };
    }

    const resolvedSlots: Record<string, string> = {};
    for (const slot of template.slots) {
      resolvedSlots[slot.key] = providedSlots[slot.key] ?? slot.fallback ?? "";
    }

    const missingSlot = this.pickHighestVOISlot(template.slots, providedSlots);
    const options = template.options.map((opt) => ({
      label: this.interpolate(opt.label, resolvedSlots),
      rationale: this.interpolate(opt.rationale, resolvedSlots)
    }));

    const learningHints = (template.learning ?? []).map((hint) => ({
      key: this.interpolate(hint.key, resolvedSlots),
      value: this.interpolate(hint.value, resolvedSlots)
    }));

    return {
      intent,
      microQuestion: missingSlot?.question,
      options,
      tinyAction: template.tinyAction,
      learningHints
    };
  }

  private pickHighestVOISlot(slots: any[], provided: Record<string, string | undefined>) {
    const missing = slots.filter((slot) => !provided[slot.key]);
    return missing.sort((a, b) => (b.voi ?? 0.5) - (a.voi ?? 0.5))[0];
  }

  private interpolate(text: string, slots: Record<string, string>): string {
    return text.replace(/\$\{([^}]+)}/g, (_, key) => slots[key.trim()] ?? "");
  }
}

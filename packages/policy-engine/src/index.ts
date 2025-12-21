import { defaultEventBus } from "@sakhi/event-bus";
import type { ContextPack, PlanGraph } from "@sakhi/contracts";
import { extractTonePreference } from "./preferences";
import type { LLMRenderer } from "./llmRenderer";
import { StubLLMRenderer } from "./llmRenderer";
export { OpenRouterLLMRenderer } from "./openrouterRenderer";

type ReplyOptions = {
  voice?: "calm" | "bright" | "steady" | "whisper";
  pacing?: "slow" | "medium" | "fast";
};

type ToneProfile = {
  style: "warm" | "encouraging" | "focused" | "lowkey";
  pacing: ReplyOptions["pacing"];
  voice: ReplyOptions["voice"];
};

export type PolicyEngineDeps = {
  eventBus?: typeof defaultEventBus;
  renderer?: LLMRenderer;
};

export class PolicyEngine {
  private readonly bus;
  private readonly renderer: LLMRenderer;

  constructor({ eventBus = defaultEventBus, renderer }: PolicyEngineDeps & { renderer?: LLMRenderer } = {}) {
    this.bus = eventBus;
    this.renderer = renderer ?? new StubLLMRenderer();
  }

  start() {
    this.bus.subscribe("plan.ready", async ({ message_id, context, plan }) => {
      const tone = this.selectTone(context, plan);
      const text = await this.renderReply(plan, context, tone);
      await this.bus.publish("reply.rendered", {
        message_id,
        plan_id: undefined,
        response: {
          text,
          tone: tone.style,
          metadata: { pacing: tone.pacing, voice: tone.voice }
        }
      });
    });
  }

  private selectTone(context: ContextPack, plan: PlanGraph): ToneProfile {
    const tonePref = extractTonePreference(context);
    const quietHours = context.constraints?.quiet_hours ?? [];
    const nowIso = context.now.clock;
    const isQuiet = quietHours.some(([start, end]) => nowIso >= start && nowIso <= end);
    const lowEnergy = context.rhythms?.awareness_coherence !== undefined && context.rhythms.awareness_coherence < 0.45;

    if (isQuiet || lowEnergy) {
      return { style: "lowkey", pacing: "slow", voice: "whisper" };
    }
    if (plan.objective_now === "listen") {
      return { style: "warm", pacing: "slow", voice: "calm" };
    }
    if (plan.objective_now === "encourage") {
      return { style: "encouraging", pacing: "medium", voice: "bright" };
    }
    if (tonePref.style) {
      return {
        style: tonePref.style,
        pacing: tonePref.pacing ?? "medium",
        voice: tonePref.voice ?? "calm"
      };
    }
    const circadian = context.rhythms?.circadian_phase;
    if (circadian === "evening") {
      return { style: "focused", pacing: "slow", voice: "steady" };
    }
    return { style: "focused", pacing: "medium", voice: "steady" };
  }

  private async renderReply(plan: PlanGraph, context: ContextPack, tone: ToneProfile): Promise<string> {
    const opener = this.buildOpener(tone);
    const body = this.describePlanSteps(plan);
    const question = plan.steps.find((step) => step.type === "question")?.template;
    const closer = tone.style === "encouraging" ? "Let me know what lands and we’ll take the next tiny step." : "I’ve got room to adjust it if needed.";
    const segments = [opener, body, question, closer].filter(Boolean);
    const fallback = segments.join(" ").trim();
    if (context.semantic_profile?.preferences?.["tone.renderer"] === "llm") {
      try {
        return await this.renderer.render(plan, context, tone.style);
      } catch {
        return fallback;
      }
    }
    return fallback;
  }

  private buildOpener(tone: ToneProfile): string {
    switch (tone.style) {
      case "warm":
        return "I’m taking a soft breath with you.";
      case "encouraging":
        return "Love that momentum.";
      case "lowkey":
        return "Keeping it gentle so you can wind down.";
      default:
        return "Here’s the snapshot.";
    }
  }

  private describePlanSteps(plan: PlanGraph): string {
    const parts: string[] = [];
    for (const step of plan.steps) {
      if (step.type === "reflection") {
        parts.push(step.text_template);
      } else if (step.type === "action.create") {
        parts.push(`I logged “${step.payload.title}” so it doesn’t float around.`);
      } else if (step.type === "calendar.block.propose") {
        parts.push(`Suggested a block for ${step.payload.title ?? "focus"}.`);
      } else if (step.type === "nudge.schedule") {
        parts.push(`Will ping you about ${step.payload.title?.toLowerCase()}.`);
      }
    }
    return parts.join(" ");
  }
}

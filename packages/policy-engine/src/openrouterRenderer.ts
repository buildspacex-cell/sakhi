import type { PlanGraph, ContextPack } from "@sakhi/contracts";

export type OpenRouterRendererConfig = {
  apiKey: string;
  model?: string;
  baseUrl?: string;
  toxicityThreshold?: number;
};

export class OpenRouterLLMRenderer {
  private readonly apiKey: string;
  private readonly model: string;
  private readonly baseUrl: string;
  private readonly toxicityThreshold: number;

  constructor({ apiKey, model = "deepseek/deepseek-chat", baseUrl = "https://openrouter.ai/api/v1/chat/completions", toxicityThreshold = 0.5 }: OpenRouterRendererConfig) {
    this.apiKey = apiKey;
    this.model = model;
    this.baseUrl = baseUrl;
    this.toxicityThreshold = toxicityThreshold;
  }

  async render(plan: PlanGraph, context: ContextPack, tone: string): Promise<string> {
    const system = this.buildSystemPrompt(tone);
    const user = this.buildUserPrompt(plan, context);
    const response = await fetch(this.baseUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: "system", content: system },
          { role: "user", content: user }
        ]
      })
    });
    if (!response.ok) {
      throw new Error(`OpenRouter request failed: ${response.status} ${await response.text()}`);
    }
    const data = await response.json();
    const choice = data.choices?.[0]?.message?.content;
    if (!choice) throw new Error("No completion returned");
    if (await this.isToxic(choice)) {
      throw new Error("LLM reply flagged by safety filter");
    }
    return choice.trim();
  }

  private buildSystemPrompt(tone: string): string {
    return `You are Sakhi, a gentle AI companion. Reply in a ${tone} manner, under 120 words, weaving in a micro-reflection. Never produce harmful or unsafe content.`;
  }

  private buildUserPrompt(plan: PlanGraph, context: ContextPack): string {
    const steps = plan.steps
      .map((step) => {
        if (step.type === "reflection") return `Reflection: ${step.text_template}`;
        if (step.type === "question") return `Ask: ${step.template}`;
        if (step.type === "action.create") return `Task: ${step.payload.title}`;
        if (step.type === "calendar.block.propose") return `Block: ${step.payload.title}`;
        if (step.type === "nudge.schedule") return `Nudge: ${step.payload.title}`;
        return "";
      })
      .filter(Boolean)
      .join("\n");
    const mood = context.semantic_profile?.traits?.mood ?? "unknown";
    return `User mood: ${mood}\nObjectives:\n${steps}\nCompose the reply now.`;
  }

  private async isToxic(text: string): Promise<boolean> {
    const result = await fetch("https://api.openai.com/v1/moderations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.OPENAI_API_KEY ?? ""}`
      },
      body: JSON.stringify({ input: text })
    });
    if (!result.ok) return false;
    const data = await result.json();
    const score = data.results?.[0]?.category_scores?.harassment ?? 0;
    return score > this.toxicityThreshold;
  }
}

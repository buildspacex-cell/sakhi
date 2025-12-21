import { defaultEventBus } from "@sakhi/event-bus";
import type { MemoryService } from "@sakhi/memory-service";
import { ShortTermInteractionSchema, EpisodicRecordSchema, SemanticTraitSchema, type PlanGraph } from "@sakhi/contracts";
import crypto from "node:crypto";

const genId = () => crypto.randomUUID();

export type LearningEngineDeps = {
  memoryService: MemoryService;
  eventBus?: typeof defaultEventBus;
  consolidationIntervalMs?: number;
  decayAfterDays?: number;
};

export class LearningEngine {
  private readonly memory: MemoryService;
  private readonly bus: typeof defaultEventBus;
  private readonly consolidationIntervalMs: number;
  private readonly decayAfterMs: number;
  private consolidationTimer: ReturnType<typeof setInterval> | null = null;
  private readonly trackedUsers = new Set<string>();

  constructor({ memoryService, eventBus = defaultEventBus, consolidationIntervalMs = 86_400_000, decayAfterDays = 14 }: LearningEngineDeps) {
    this.memory = memoryService;
    this.bus = eventBus;
    this.consolidationIntervalMs = consolidationIntervalMs;
    this.decayAfterMs = decayAfterDays * 24 * 60 * 60 * 1000;
  }

  start() {
    this.bus.subscribe("plan.ready", async ({ message_id, context, plan, extras }) => {
      await this.handlePlanReady(message_id, context.user_id, plan, extras);
    });
    if (this.consolidationIntervalMs > 0) {
      this.startConsolidationTimer();
    }
  }

  stop() {
    if (this.consolidationTimer) {
      clearInterval(this.consolidationTimer);
      this.consolidationTimer = null;
    }
  }

  private async handlePlanReady(messageId: string, userId: string, plan: PlanGraph, extras?: Record<string, unknown>) {
    const nowIso = new Date().toISOString();
    const message = {
      schema_version: "0.1.0",
      id: messageId,
      user_id: userId,
      timestamp: nowIso,
      content: { text: plan.steps.find((step: any) => step.type === "reflection")?.text_template ?? plan.objective_now, modality: "text", locale: "en-US" },
      source: { channel: "learning-engine" },
      metadata: { timezone: "UTC" }
    };
    const stmRecord = ShortTermInteractionSchema.parse({
      schema_version: "0.1.0",
      id: genId(),
      timestamp: nowIso,
      message,
      facets: []
    });
    await this.memory.appendShortTerm(userId, stmRecord);

    const episodicRecord = EpisodicRecordSchema.parse({
      schema_version: "0.1.0",
      id: genId(),
      when: nowIso,
      text: `Plan executed: ${plan.objective_now}`,
      facets: [],
      outcome: "planned"
    });
    await this.memory.appendEpisodic(userId, episodicRecord);

    const hints = Array.isArray((extras as any)?.learningHints) ? ((extras as any).learningHints as Array<{ key: string; value: string }>) : [];
    const updatedTraits = [];
    for (const hint of hints) {
      const trait = await this.upsertTraitFromHint(userId, hint.key, hint.value, messageId);
      if (trait) updatedTraits.push(trait);
    }
    if (updatedTraits.length) {
      await this.bus.publish("memory.updated", {
        message_id: messageId,
        traits: updatedTraits
      });
    }

    this.trackedUsers.add(userId);
  }

  private startConsolidationTimer() {
    if (this.consolidationTimer) return;
    this.consolidationTimer = setInterval(() => {
      void this.runConsolidation();
    }, this.consolidationIntervalMs);
  }

  private async runConsolidation() {
    for (const userId of this.trackedUsers) {
      await this.decayTraits(userId);
    }
  }

  private async decayTraits(userId: string) {
    const traits = await this.memory.listSemanticTraits(userId);
    const now = Date.now();
    for (const trait of traits) {
      const lastUpdated = new Date(trait.last_updated).getTime();
      if (Number.isNaN(lastUpdated) || now - lastUpdated < this.decayAfterMs) continue;
      const newConfidence = Math.max(0, trait.confidence - 0.05);
      if (newConfidence <= 0.1 && this.memory.removeSemanticTrait) {
        await this.memory.removeSemanticTrait(userId, trait.key);
        continue;
      }
      const updated = SemanticTraitSchema.parse({
        ...trait,
        confidence: newConfidence,
        last_updated: new Date().toISOString()
      });
      await this.memory.upsertSemanticTrait(userId, updated);
    }
  }

  private async upsertTraitFromHint(userId: string, key: string, value: string, sourceId: string) {
    const existing = await this.memory.getSemanticTrait(userId, key);
    const nowIso = new Date().toISOString();
    let confidence = existing?.confidence ?? 0.45;
    let resolvedValue: unknown = value;
    let firstSeen = existing?.first_seen ?? nowIso;
    let evidence = existing?.evidence ?? [];

    if (existing) {
      if (String(existing.value) === value) {
        confidence = Math.min(1, confidence + 0.1);
      } else {
        confidence = Math.max(0.2, confidence - 0.2);
        if (confidence < 0.35) {
          resolvedValue = value;
          confidence = 0.4;
          firstSeen = nowIso;
        } else {
          resolvedValue = existing.value;
        }
      }
    }

    evidence = [...evidence, { source_id: sourceId, noted_at: nowIso }];
    if (evidence.length > 10) evidence = evidence.slice(-10);

    const trait = SemanticTraitSchema.parse({
      schema_version: "0.1.0",
      key,
      value: resolvedValue,
      confidence,
      first_seen: firstSeen,
      last_updated: nowIso,
      evidence
    });
    await this.memory.upsertSemanticTrait(userId, trait);
    return trait;
  }
}

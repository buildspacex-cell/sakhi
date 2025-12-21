import { ContextPackSchema, type ContextPack, type EpisodicRecord, type ShortTermInteraction } from "@sakhi/contracts";
import { DefaultContextRecipe } from "./defaultRecipe";
import type {
  ContextBuilder,
  ContextBuilderInput,
  ContextRecipe,
  MemoryStore,
  RhythmEngine,
  ScheduleStore
} from "./types";
import type { EmbeddingClient } from "./embeddingClient";
import { NullEmbeddingClient } from "./embeddingClient";

export type ContextBuilderDeps = {
  memoryStore: MemoryStore;
  scheduleStore: ScheduleStore;
  rhythmEngine: RhythmEngine;
  embeddingClient?: EmbeddingClient;
  recipe?: ContextRecipe;
};

export class WorkingContextBuilder implements ContextBuilder {
  private readonly memoryStore: MemoryStore;
  private readonly scheduleStore: ScheduleStore;
  private readonly rhythmEngine: RhythmEngine;
  private readonly embeddingClient: EmbeddingClient;
  private readonly recipe: ContextRecipe;

  constructor({ memoryStore, scheduleStore, rhythmEngine, embeddingClient, recipe }: ContextBuilderDeps) {
    this.memoryStore = memoryStore;
    this.scheduleStore = scheduleStore;
    this.rhythmEngine = rhythmEngine;
    this.embeddingClient = embeddingClient ?? new NullEmbeddingClient();
    this.recipe = recipe ?? DefaultContextRecipe;
  }

  async build(input: ContextBuilderInput): Promise<ContextPack> {
    const { message, userId, turnId, now } = input;
    const recipe = input.recipe ?? this.recipe;

    const queryEmbedding = await this.safeEmbed(message.content.text);

    const [workingItems, episodicCandidates, semanticProfile, rhythms, schedule] = await Promise.all([
      this.memoryStore.getShortTermBuffer(userId, recipe.workingLimit),
      this.memoryStore.getEpisodicHits({
        userId,
        queryEmbedding,
        textQuery: message.content.text,
        limit: recipe.episodicLimit * 3
      }),
      this.memoryStore.getSemanticProfile(userId),
      this.rhythmEngine.getRhythms(userId, now),
      this.scheduleStore.getWindow(userId, {
        start: now,
        end: new Date(now.getTime() + 72 * 60 * 60 * 1000)
      })
    ]);

    const episodicHits = this.applyDiversityGuard(episodicCandidates, recipe.episodicLimit, recipe.episodicDiversity ?? 0.6);

    const context: ContextPack = {
      schema_version: ContextPackSchema.shape.schema_version.value ?? "0.1.0",
      user_id: userId,
      turn_id: turnId,
      now: {
        clock: now.toISOString(),
        weekday: now.toLocaleDateString("en-US", { weekday: "long" }),
        season: this.getSeason(now)
      },
      rhythms,
      working: workingItems.map((item) => this.simplifyShortTerm(item)),
      episodic_hits: episodicHits.map((ep) => ({
        id: ep.id,
        when: ep.when,
        summary: ep.text,
        relevance: ep.relevance,
        link: ep.links?.[0]
      })),
      semantic_profile: semanticProfile,
      schedule_window: {
        events: schedule.events,
        free_blocks: schedule.freeBlocks
      },
      goals: {
        short_term: [],
        long_term: []
      },
      constraints: {
        quiet_hours: this.extractQuietHours(message),
        do_not_disturb: message.metadata?.extras?.["dnd"] as boolean | undefined
      },
      tokens_estimate: this.estimateTokens(workingItems, episodicHits, semanticProfile, input.tokensBudget)
    };

    return ContextPackSchema.parse(context);
  }

  private simplifyShortTerm(item: ShortTermInteraction) {
    return {
      id: item.id,
      message_id: item.message.id,
      text: item.message.content.text,
      timestamp: item.timestamp,
      facets: item.facets
    };
  }

  private async safeEmbed(text: string): Promise<number[]> {
    try {
      const vector = await this.embeddingClient.embed(text);
      return vector || [];
    } catch {
      return [];
    }
  }

  private applyDiversityGuard(records: (EpisodicRecord & { relevance?: number })[], limit: number, threshold: number): EpisodicRecord[] {
    const selected: EpisodicRecord[] = [];
    const seen: string[] = [];
    for (const record of records) {
      const fingerprint = record.text.slice(0, 80).toLowerCase();
      if (seen.some((entry) => this.similarity(entry, fingerprint) > threshold)) continue;
      seen.push(fingerprint);
      selected.push(record);
      if (selected.length >= limit) break;
    }
    return selected;
  }

  private similarity(a: string, b: string): number {
    const setA = new Set(a.split(/\s+/));
    const setB = new Set(b.split(/\s+/));
    const intersection = [...setA].filter((word) => setB.has(word));
    return intersection.length / Math.max(setA.size, 1);
  }

  private estimateTokens(working: ShortTermInteraction[], episodic: EpisodicRecord[], semantic: any, budget?: number): number {
    const wordToToken = (text: string) => Math.ceil(text.length / 4);
    const workingTokens = working.reduce((acc, item) => acc + wordToToken(item.message.content.text), 0);
    const episodicTokens = episodic.reduce((acc, item) => acc + wordToToken(item.text), 0);
    const semanticTokens = JSON.stringify(semantic).length / 4;
    const total = Math.round(workingTokens + episodicTokens + semanticTokens);
    if (!budget) return total;
    return Math.min(total, budget);
  }
}

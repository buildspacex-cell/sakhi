import type {
  ContextPack,
  EpisodicRecord,
  Message,
  SemanticTrait,
  PreferenceRecord,
  ShortTermInteraction
} from "@sakhi/contracts";

export interface MemoryStore {
  getShortTermBuffer(userId: string, limit: number): Promise<ShortTermInteraction[]>;
  getEpisodicHits(params: { userId: string; queryEmbedding?: number[]; textQuery?: string; limit: number }): Promise<(EpisodicRecord & { relevance?: number })[]>;
  getSemanticProfile(userId: string): Promise<{
    traits: Record<string, unknown>;
    preferences: Record<string, unknown>;
    values: string[];
  }>;
}

export interface ScheduleStore {
  getWindow(userId: string, window: { start: Date; end: Date }): Promise<{
    events: Array<{
      id: string;
      title: string;
      start: string;
      end: string;
      location?: string;
      category?: string;
    }>;
    freeBlocks: Array<{
      start: string;
      end: string;
      energy?: "low" | "medium" | "high";
    }>;
  }>;
}

export interface RhythmEngine {
  getRhythms(userId: string, at: Date): Promise<{
    circadian_phase?: string;
    breath_rate?: number;
    awareness_coherence?: number;
  }>;
}

export type ContextRecipe = {
  workingLimit: number;
  episodicLimit: number;
  episodicDiversity?: number;
  hardPins: (input: ContextBuilderInput) => string[];
  softPins: (input: ContextBuilderInput) => string[];
};

export interface ContextBuilderInput {
  userId: string;
  turnId: string;
  message: Message;
  now: Date;
  tokensBudget?: number;
  recipe?: ContextRecipe;
}

export interface ContextBuilder {
  build(input: ContextBuilderInput): Promise<ContextPack>;
}

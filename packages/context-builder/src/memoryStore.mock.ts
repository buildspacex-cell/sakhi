import type {
  ShortTermInteraction,
  EpisodicRecord
} from "@sakhi/contracts";
import type { MemoryStore } from "./types";

export class InMemoryMemoryStore implements MemoryStore {
  private shortTerm: Map<string, ShortTermInteraction[]> = new Map();
  private episodic: Map<string, EpisodicRecord[]> = new Map();
  private profiles: Map<string, { traits: Record<string, unknown>; preferences: Record<string, unknown>; values: string[] }> = new Map();

  setShortTerm(userId: string, items: ShortTermInteraction[]): void {
    this.shortTerm.set(userId, items);
  }

  setEpisodic(userId: string, records: EpisodicRecord[]): void {
    this.episodic.set(userId, records);
  }

  setProfile(userId: string, profile: { traits: Record<string, unknown>; preferences: Record<string, unknown>; values: string[] }): void {
    this.profiles.set(userId, profile);
  }

  async getShortTermBuffer(userId: string, limit: number): Promise<ShortTermInteraction[]> {
    return (this.shortTerm.get(userId) ?? []).slice(0, limit);
  }

  async getEpisodicHits(params: { userId: string; query: string; limit: number; }): Promise<EpisodicRecord[]> {
    const list = this.episodic.get(params.userId) ?? [];
    return list.slice(0, params.limit);
  }

  async getSemanticProfile(userId: string): Promise<{ traits: Record<string, unknown>; preferences: Record<string, unknown>; values: string[]; }> {
    return this.profiles.get(userId) ?? { traits: {}, preferences: {}, values: [] };
  }
}

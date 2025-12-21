import type {
  ShortTermInteraction,
  EpisodicRecord,
  SemanticTrait,
  PreferenceRecord,
  IdentityEdge
} from "@sakhi/contracts";
import type { MemoryService } from "./types";

const MAX_STM_DEFAULT = 25;

export class InMemoryMemoryService implements MemoryService {
  private shortTerm = new Map<string, ShortTermInteraction[]>();
  private episodic = new Map<string, EpisodicRecord[]>();
  private traits = new Map<string, SemanticTrait[]>();
  private preferences = new Map<string, PreferenceRecord[]>();
  private edges = new Map<string, IdentityEdge[]>();

  constructor(private readonly options: { maxShortTerm?: number } = {}) {}

  async appendShortTerm(userId: string, record: ShortTermInteraction): Promise<void> {
    const buffer = this.shortTerm.get(userId) ?? [];
    buffer.unshift(record);
    const max = this.options.maxShortTerm ?? MAX_STM_DEFAULT;
    this.shortTerm.set(userId, buffer.slice(0, max));
  }

  async getShortTerm(userId: string, limit: number): Promise<ShortTermInteraction[]> {
    return (this.shortTerm.get(userId) ?? []).slice(0, limit);
  }

  async appendEpisodic(userId: string, record: EpisodicRecord): Promise<void> {
    const list = this.episodic.get(userId) ?? [];
    list.unshift(record);
    this.episodic.set(userId, list);
  }

  async searchEpisodic(userId: string, query: string, limit: number): Promise<EpisodicRecord[]> {
    const list = this.episodic.get(userId) ?? [];
    const lower = query.toLowerCase();
    return list.filter((rec) => rec.text.toLowerCase().includes(lower)).slice(0, limit);
  }

  async upsertSemanticTrait(userId: string, trait: SemanticTrait): Promise<void> {
    const items = this.traits.get(userId) ?? [];
    const idx = items.findIndex((t) => t.key === trait.key);
    if (idx >= 0) items[idx] = trait;
    else items.push(trait);
    this.traits.set(userId, items);
  }

  async getSemanticTrait(userId: string, key: string): Promise<SemanticTrait | null> {
    const items = this.traits.get(userId) ?? [];
    return items.find((t) => t.key === key) ?? null;
  }

  async listSemanticTraits(userId: string): Promise<SemanticTrait[]> {
    return this.traits.get(userId) ?? [];
  }

  async removeSemanticTrait(userId: string, key: string): Promise<void> {
    const items = this.traits.get(userId) ?? [];
    this.traits.set(userId, items.filter((t) => t.key !== key));
  }

  async upsertPreference(userId: string, pref: PreferenceRecord): Promise<void> {
    const items = this.preferences.get(userId) ?? [];
    const idx = items.findIndex((p) => p.key === pref.key && p.scope === pref.scope);
    if (idx >= 0) items[idx] = pref;
    else items.push(pref);
    this.preferences.set(userId, items);
  }

  async listPreferences(userId: string): Promise<PreferenceRecord[]> {
    return this.preferences.get(userId) ?? [];
  }

  async upsertIdentityEdge(userId: string, edge: IdentityEdge): Promise<void> {
    const items = this.edges.get(userId) ?? [];
    const idx = items.findIndex((e) => e.from === edge.from && e.to === edge.to && e.relationship === edge.relationship);
    if (idx >= 0) items[idx] = edge;
    else items.push(edge);
    this.edges.set(userId, items);
  }

  async listIdentityEdges(userId: string): Promise<IdentityEdge[]> {
    return this.edges.get(userId) ?? [];
  }
}

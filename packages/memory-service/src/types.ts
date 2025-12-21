import type {
  ShortTermInteraction,
  EpisodicRecord,
  SemanticTrait,
  PreferenceRecord,
  IdentityEdge
} from "@sakhi/contracts";

export interface MemoryService {
  appendShortTerm(userId: string, record: ShortTermInteraction): Promise<void>;
  getShortTerm(userId: string, limit: number): Promise<ShortTermInteraction[]>;

  appendEpisodic(userId: string, record: EpisodicRecord): Promise<void>;
  searchEpisodic(userId: string, query: string, limit: number): Promise<EpisodicRecord[]>;

  upsertSemanticTrait(userId: string, trait: SemanticTrait): Promise<void>;
  getSemanticTrait(userId: string, key: string): Promise<SemanticTrait | null>;
  listSemanticTraits(userId: string): Promise<SemanticTrait[]>;
  removeSemanticTrait?(userId: string, key: string): Promise<void>;

  upsertPreference(userId: string, pref: PreferenceRecord): Promise<void>;
  listPreferences(userId: string): Promise<PreferenceRecord[]>;

  upsertIdentityEdge(userId: string, edge: IdentityEdge): Promise<void>;
  listIdentityEdges(userId: string): Promise<IdentityEdge[]>;
}

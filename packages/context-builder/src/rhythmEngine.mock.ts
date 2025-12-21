import type { RhythmEngine } from "./types";

export class StaticRhythmEngine implements RhythmEngine {
  private rhythms = new Map<string, { circadian_phase?: string; breath_rate?: number; awareness_coherence?: number }>();

  set(userId: string, data: { circadian_phase?: string; breath_rate?: number; awareness_coherence?: number }): void {
    this.rhythms.set(userId, data);
  }

  async getRhythms(userId: string, _at: Date): Promise<{ circadian_phase?: string; breath_rate?: number; awareness_coherence?: number }> {
    return this.rhythms.get(userId) ?? {};
  }
}

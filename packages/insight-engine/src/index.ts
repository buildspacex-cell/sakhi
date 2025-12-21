import type { MemoryService } from "@sakhi/memory-service";
import { EpisodicRecord } from "@sakhi/contracts";

export type Insight = {
  userId: string;
  weekOf: string;
  highlights: string[];
  mood?: string;
};

export class InsightEngine {
  constructor(private readonly memory: MemoryService) {}

  async synthesizeWeekly(userId: string, weekStart: Date): Promise<Insight> {
    const weekEnd = new Date(weekStart.getTime() + 7 * 24 * 60 * 60 * 1000);
    const episodic = await this.memory.searchEpisodic(userId, "", 100);
    const filtered = episodic.filter((record) => {
      const when = new Date(record.when);
      return when >= weekStart && when < weekEnd;
    });
    const highlights = this.summarizeHighlights(filtered);
    return {
      userId,
      weekOf: weekStart.toISOString().split("T")[0],
      highlights,
      mood: this.estimateMood(filtered)
    };
  }

  private summarizeHighlights(records: EpisodicRecord[]): string[] {
    return records.slice(0, 3).map((rec) => rec.text.slice(0, 140));
  }

  private estimateMood(records: EpisodicRecord[]): string | undefined {
    if (!records.length) return undefined;
    const negativeHints = ["overwhelmed", "tired", "drained"];
    const positiveHints = ["excited", "energized", "grateful"];
    const text = records.map((r) => r.text.toLowerCase()).join(" ");
    const neg = negativeHints.some((hint) => text.includes(hint));
    const pos = positiveHints.some((hint) => text.includes(hint));
    if (pos && !neg) return "positive";
    if (neg && !pos) return "low";
    return "mixed";
  }
}

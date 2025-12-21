import type { ScheduleStore } from "./types";

export class InMemoryScheduleStore implements ScheduleStore {
  private windows = new Map<
    string,
    {
      events: Array<{ id: string; title: string; start: string; end: string; location?: string; category?: string }>;
      freeBlocks: Array<{ start: string; end: string; energy?: "low" | "medium" | "high" }>;
    }
  >();

  setWindow(userId: string, data: { events: Array<{ id: string; title: string; start: string; end: string; location?: string; category?: string }>; freeBlocks: Array<{ start: string; end: string; energy?: "low" | "medium" | "high" }> }): void {
    this.windows.set(userId, data);
  }

  async getWindow(
    userId: string,
    _window: { start: Date; end: Date }
  ): Promise<{ events: Array<{ id: string; title: string; start: string; end: string; location?: string; category?: string }>; freeBlocks: Array<{ start: string; end: string; energy?: "low" | "medium" | "high" }> }> {
    return this.windows.get(userId) ?? { events: [], freeBlocks: [] };
  }
}

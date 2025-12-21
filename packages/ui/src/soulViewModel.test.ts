import { computeCoherence, imbalanceScore, normalizeSoulState, timelineSeries } from "./soulViewModel";

describe("soulViewModel", () => {
  it("normalizes soul state safely", () => {
    const normalized = normalizeSoulState({ core_values: "not-list", confidence: 0.5 });
    expect(normalized.core_values).toEqual([]);
    expect(normalized.confidence).toBe(0.5);
  });

  it("computes coherence/imbalance", () => {
    const summary: any = { top_shadow: ["a", "b"], top_light: ["c"] };
    const coherence = computeCoherence(summary);
    expect(coherence).toBeGreaterThan(0);
    const imbalance = imbalanceScore(summary);
    expect(imbalance).toBeGreaterThan(0);
  });

  it("builds timeline series", () => {
    const series = timelineSeries([{ ts: "t1", shadow: [1], light: [1, 2], conflict: [], friction: [] }]);
    expect(series[0].shadow).toBe(1);
    expect(series[0].light).toBe(2);
  });
});

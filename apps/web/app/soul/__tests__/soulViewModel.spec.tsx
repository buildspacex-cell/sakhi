import { normalizeSoulState, computeCoherence, timelineSeries } from "@ui/soulViewModel";

describe("soulViewModel (web)", () => {
  it("normalizes safely", () => {
    const normalized = normalizeSoulState({ core_values: "x", confidence: 0.4 });
    expect(normalized.core_values).toEqual([]);
    expect(normalized.confidence).toBe(0.4);
  });

  it("computes coherence", () => {
    const summary = { top_shadow: ["a"], top_light: ["b", "c"] };
    expect(computeCoherence(summary)).toBeGreaterThan(0);
  });

  it("builds timeline series", () => {
    const series = timelineSeries([{ ts: "t1", shadow: [1], light: [1, 2], conflict: [], friction: [] }]);
    expect(series[0].shadow).toBe(1);
    expect(series[0].light).toBe(2);
  });
});

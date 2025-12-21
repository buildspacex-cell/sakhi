import React from "react";
import renderer from "react-test-renderer";
import SoulHomeScreen from "../index";

jest.mock("@ui/soulViewModel", () => ({
  normalizeSoulState: (v: any) => v,
  summarizeSoul: (state: any, summary: any) => ({
    shadow: ["doubt"],
    light: ["optimism"],
    coherence: 0.7,
    friction: summary?.dominant_friction || "none",
  }),
}));

global.fetch = jest.fn().mockResolvedValue({
  json: async () => ({
    core_values: ["growth"],
    identity_themes: ["learning"],
    dominant_friction: "balance vs overwork",
  }),
}) as any;

describe("SoulHomeScreen snapshot", () => {
  it("matches snapshot", () => {
    const tree = renderer.create(<SoulHomeScreen />).toJSON();
    expect(tree).toMatchSnapshot();
  });
});

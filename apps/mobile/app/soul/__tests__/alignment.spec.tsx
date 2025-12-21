import React from "react";
import renderer from "react-test-renderer";
import SoulAlignmentScreen from "../alignment";

global.fetch = jest.fn().mockResolvedValue({
  json: async () => ({ alignment_score: 0.5, conflict_zones: ["overwork"], action_suggestions: ["rest"] }),
}) as any;

describe("SoulAlignmentScreen", () => {
  it("renders alignment view", () => {
    const tree = renderer.create(<SoulAlignmentScreen />).toJSON();
    expect(tree).toBeTruthy();
  });
});

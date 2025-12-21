import React from "react";
import renderer from "react-test-renderer";
import SoulNarrativeScreen from "../narrative";

global.fetch = jest.fn().mockResolvedValue({
  json: async () => ({ identity_arc: "arc", soul_archetype: "sage" }),
}) as any;

describe("SoulNarrativeScreen", () => {
  it("renders narrative view", () => {
    const tree = renderer.create(<SoulNarrativeScreen />).toJSON();
    expect(tree).toBeTruthy();
  });
});

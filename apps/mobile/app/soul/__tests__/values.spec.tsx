import React from "react";
import renderer from "react-test-renderer";
import SoulValuesScreen from "../values";

jest.mock("@ui/soulViewModel", () => ({
  normalizeSoulState: (v: any) => v,
}));

global.fetch = jest.fn().mockResolvedValue({
  json: async () => ({
    core_values: ["growth", "balance"],
    longing: ["rest"],
    aversions: ["burnout"],
  }),
}) as any;

describe("SoulValuesScreen", () => {
  it("renders values view", () => {
    const tree = renderer.create(<SoulValuesScreen />).toJSON();
    expect(tree).toBeTruthy();
  });
});

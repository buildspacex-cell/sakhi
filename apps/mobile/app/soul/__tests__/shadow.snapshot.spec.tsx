import React from "react";
import renderer from "react-test-renderer";
import SoulShadowScreen from "../shadow";

jest.mock("@ui/soulViewModel", () => ({
  normalizeSoulState: (v: any) => v,
  summarizeSoul: (_s: any, _sum: any) => ({
    shadow: ["doubt"],
    light: ["optimism"],
    friction: "balance vs overwork",
  }),
}));

global.fetch = jest.fn().mockResolvedValue({
  json: async () => ({}),
}) as any;

describe("SoulShadowScreen snapshot", () => {
  it("matches snapshot", () => {
    const tree = renderer.create(<SoulShadowScreen />).toJSON();
    expect(tree).toMatchSnapshot();
  });
});

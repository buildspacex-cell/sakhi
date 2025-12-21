import React from "react";
import renderer from "react-test-renderer";
import SoulFrictionScreen from "../friction";

jest.mock("@ui/soulViewModel", () => ({
  timelineSeries: () => [
    { ts: "t1", shadow: 1, light: 1, conflict: 2, friction: 1 },
    { ts: "t2", shadow: 1, light: 1, conflict: 1, friction: 3 },
  ],
}));

global.fetch = jest.fn().mockResolvedValue({
  json: async () => ({}),
}) as any;

describe("SoulFrictionScreen", () => {
  it("renders friction view", () => {
    const tree = renderer.create(<SoulFrictionScreen />).toJSON();
    expect(tree).toBeTruthy();
  });
});

import React from "react";
import renderer from "react-test-renderer";
import SoulTimelineScreen from "../timeline";

jest.mock("@ui/soulViewModel", () => ({
  timelineSeries: () => [
    { ts: "t1", shadow: 1, light: 2, conflict: 0, friction: 0 },
    { ts: "t2", shadow: 2, light: 1, conflict: 1, friction: 0 },
  ],
}));

global.fetch = jest.fn().mockResolvedValue({ json: async () => [] }) as any;

describe("SoulTimelineScreen", () => {
  it("renders without crashing", () => {
    const tree = renderer.create(<SoulTimelineScreen />).toJSON();
    expect(tree).toBeTruthy();
  });
});

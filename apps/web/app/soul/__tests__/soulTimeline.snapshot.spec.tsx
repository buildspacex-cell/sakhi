import React from "react";
import { render, waitFor } from "@testing-library/react";
import SoulTimelinePage from "../timeline/page";
import { server } from "./mswSetup";

describe("Soul timeline snapshot", () => {
  it("renders with matrix and chart", async () => {
    const view = render(<SoulTimelinePage />);
    await waitFor(() => view.getByText(/Timeline/i));
    expect(view.asFragment()).toMatchSnapshot();
  });
});

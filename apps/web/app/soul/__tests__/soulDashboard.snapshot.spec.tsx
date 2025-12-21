import React from "react";
import { render, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulDashboard from "../page";
import { server } from "./mswSetup";

describe("Soul dashboard snapshot", () => {
  it("matches snapshot with mocked data", async () => {
    const view = render(<SoulDashboard />);
    await waitFor(() => view.getByText(/Identity Snapshot/i));
    expect(view.asFragment()).toMatchSnapshot();
  });
});

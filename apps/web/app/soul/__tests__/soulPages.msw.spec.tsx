import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulDashboard from "../page";
import SoulTimelinePage from "../timeline/page";
import { server } from "./mswSetup";

describe("Soul pages with MSW", () => {
  it("renders dashboard with mocked data", async () => {
    render(<SoulDashboard />);
    await waitFor(() => expect(screen.getByText(/growth/i)).toBeInTheDocument());
    expect(screen.getByText(/Identity Snapshot/i)).toBeInTheDocument();
  });

  it("renders timeline chart data", async () => {
    render(<SoulTimelinePage />);
    await waitFor(() => expect(screen.getByText(/Soul Timeline/i)).toBeInTheDocument());
  });
});

import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulDashboard from "../page";

// Minimal mock for fetch because page uses SWR; we render a placeholder by mocking global fetch
global.fetch = jest.fn().mockResolvedValue({
  json: async () => ({}),
}) as any;

describe("Soul dashboard", () => {
  it("renders heading", () => {
    render(<SoulDashboard />);
    expect(screen.getByText(/Identity Snapshot/i)).toBeInTheDocument();
  });
});

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulValuesPage from "../values/page";
import { server } from "./mswSetup";

describe("Soul values page visuals", () => {
  it("renders values wheel with mocked data", async () => {
    render(<SoulValuesPage />);
    await waitFor(() => expect(screen.getByText(/Values & Commitments/i)).toBeInTheDocument());
    expect(screen.getByText(/Values Wheel/i)).toBeInTheDocument();
  });
});

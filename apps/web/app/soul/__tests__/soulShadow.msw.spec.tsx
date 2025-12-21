import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulShadowPage from "../shadow-work/page";
import { server } from "./mswSetup";

describe("Soul shadow page with MSW", () => {
  it("renders shadow/light content", async () => {
    render(<SoulShadowPage />);
    await waitFor(() => expect(screen.getByText(/Shadow Patterns/i)).toBeInTheDocument());
    expect(screen.getByText(/Light Patterns/i)).toBeInTheDocument();
  });
});

import React from "react";
import { render, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulValuesPage from "../values/page";
import { server } from "./mswSetup";

describe("Soul values snapshot", () => {
  it("matches snapshot with mocked data", async () => {
    const view = render(<SoulValuesPage />);
    await waitFor(() => view.getByText(/Values & Commitments/i));
    expect(view.asFragment()).toMatchSnapshot();
  });
});

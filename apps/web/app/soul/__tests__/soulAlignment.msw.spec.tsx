import React from "react";
import { render, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulAlignmentPage from "../alignment/page";
import { server } from "./mswSetup";

describe("Soul alignment MSW", () => {
  it("renders alignment with mocked data", async () => {
    const view = render(<SoulAlignmentPage />);
    await waitFor(() => view.getByText(/Alignment & Conflicts/i));
    expect(view.asFragment()).toMatchSnapshot();
  });
});

import React from "react";
import { render, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulNarrativePage from "../narrative/page";
import { server } from "./mswSetup";

describe("Soul narrative snapshot", () => {
  it("matches snapshot with mocked data", async () => {
    const view = render(<SoulNarrativePage />);
    await waitFor(() => view.getByText(/Story & Arc/i));
    expect(view.asFragment()).toMatchSnapshot();
  });
});

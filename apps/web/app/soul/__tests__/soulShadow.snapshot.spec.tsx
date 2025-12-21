import React from "react";
import { render, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SoulShadowWorkPage from "../shadow-work/page";
import { server } from "./mswSetup";

describe("Soul shadow page snapshot", () => {
  it("matches snapshot with mocked data", async () => {
    const view = render(<SoulShadowWorkPage />);
    await waitFor(() => view.getByText(/Shadow & Light/i));
    expect(view.asFragment()).toMatchSnapshot();
  });
});

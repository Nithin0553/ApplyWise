// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("shows the sign-in screen when nobody is signed in", async () => {
    render(<App />);

    // F01 owns the signed-out screen; the feature shell only appears after login.
    expect(
      await screen.findByRole("heading", { name: "Sign in to ApplyWise" }),
    ).toBeInTheDocument();
  });
});

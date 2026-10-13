// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("shows the animated brand before revealing the original sign-in form", async () => {
    render(<App />);
    expect(screen.getByRole("main", { name: "ApplyWise welcome" })).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Sign in to ApplyWise" }, { timeout: 4000 }),
    ).toBeInTheDocument();
  }, 6000);
});

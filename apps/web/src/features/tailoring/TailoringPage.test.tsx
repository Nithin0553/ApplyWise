// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { TailoringPage } from "./TailoringPage";

// Vitest is not configured with globals, so unmount between tests ourselves.
afterEach(cleanup);

describe("TailoringPage", () => {
  it("lists approved evidence with short reference labels", async () => {
    render(<TailoringPage />);

    await waitFor(() => {
      expect(screen.getByText("Associate QA Engineer")).toBeInTheDocument();
    });
    expect(screen.getByText("E1")).toBeInTheDocument();
  });

  it("shows the target job fields", async () => {
    render(<TailoringPage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("Software Engineer in Test")).toBeInTheDocument();
    });
  });
});

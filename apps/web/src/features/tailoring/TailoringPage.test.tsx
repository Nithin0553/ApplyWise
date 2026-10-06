// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../auth";
import { TailoringPage } from "./TailoringPage";

// Vitest is not configured with globals, so unmount between tests ourselves.
afterEach(cleanup);

/**
 * One approved record exactly as F02 puts it on the wire — note `id`, and the
 * lowercase enum. The page now loads evidence from the real endpoint, so the
 * fetch is stubbed rather than the feature flag being turned off: that way the
 * test covers the mapping the running application actually performs.
 */
const F02_RESPONSE = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    evidence_type: "work_experience",
    title: "Associate QA Engineer",
    organization: "Model N",
    description: "Built automated regression suites.",
    status: "approved",
  },
];

beforeEach(() => {
  // The evidence route is authenticated, so the page only fetches once it has
  // a token. Seed the one AuthProvider reads on mount.
  window.localStorage.setItem("applywise.auth.token", "test-token");

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/auth/me")) {
        return new Response(
          JSON.stringify({
            id: "99999999-9999-9999-9999-999999999999",
            email: "test@example.edu",
            full_name: "Test Person",
            role: "job_seeker",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes("/api/evidence/approved")) {
        return new Response(JSON.stringify(F02_RESPONSE), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response("{}", { status: 404 });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("TailoringPage", () => {
  it("lists approved evidence with short reference labels", async () => {
    render(
      <AuthProvider>
        <TailoringPage />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Associate QA Engineer")).toBeInTheDocument();
    });
    expect(screen.getByText("E1")).toBeInTheDocument();
  });

  it("shows the target job fields", async () => {
    render(
      <AuthProvider>
        <TailoringPage />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue("Software Engineer in Test")).toBeInTheDocument();
    });
  });
});

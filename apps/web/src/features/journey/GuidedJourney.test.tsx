// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { User } from "../auth/types";
import { estimateOverlap, readRequirements } from "./api";
import { GuidedJourney } from "./GuidedJourney";

const user: User = {
  id: "journey-test-user", full_name: "Alex Morgan", email: "alex@example.com",
  role: "job_seeker", is_active: true, created_at: "2026-10-13T00:00:00Z",
};

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.unstubAllGlobals();
});

describe("ApplyWise guided journey", () => {
  it("reveals profile questions sequentially and keeps previous answers visible", () => {
    render(<GuidedJourney user={user} token="test-token" logout={vi.fn()} />);

    expect(screen.getByText("What kind of role are you looking for?")).toBeInTheDocument();
    expect(screen.queryByText("How much professional experience do you have?")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Data Analyst" }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(screen.getByText("What kind of role are you looking for?")).toBeInTheDocument();
    expect(screen.getByText("How much professional experience do you have?")).toBeInTheDocument();
    expect(screen.getByText("Data Analyst")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "3–5 years" }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(screen.getByText("How would you like to work?")).toBeInTheDocument();
  });

  it("transfers the user's own posting to an evidence review without inventing results", async () => {
    window.localStorage.setItem(
      `applywise.journey.profile.${user.id}`,
      JSON.stringify({ career: "Software Engineer", years: "3–5 years", arrangement: "Hybrid",
        focus: ["Python"], experience: "Built API tests in Python.", resumeName: "" }),
    );
    vi.stubGlobal("scrollTo", vi.fn());
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => [],
    })));

    render(<GuidedJourney user={user} token="test-token" logout={vi.fn()} />);
    const box = screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" });
    fireEvent.change(box, { target: { value: "Requirements:\n- Python automation\n- SQL reporting" } });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(await screen.findByText("Here's what the role asks for.", {}, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByText("Python automation")).toBeInTheDocument();
    expect(screen.getByText("SQL reporting")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate resume/i })).toBeDisabled();
    expect(screen.getByText(/No evidence saved yet/)).toBeInTheDocument();
  }, 6000);
});

describe("grounded analysis helpers", () => {
  it("extracts only lines from the supplied posting", () => {
    expect(readRequirements("Required skills:\n- Python and SQL\n- Test automation")).toEqual([
      "Python and SQL", "Test automation",
    ]);
  });

  it("shows zero overlap without approved evidence instead of a fabricated score", () => {
    expect(estimateOverlap(["Python programming", "Java applications"], []).percentage).toBe(0);
  });
});

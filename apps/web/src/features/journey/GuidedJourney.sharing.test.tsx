// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../sharing", () => ({
  SharingPage: () => <h2>Sharing module connected</h2>,
}));

import type { User } from "../auth/types";
import { GuidedJourney } from "./GuidedJourney";

const user: User = {
  id: "sharing-nav-user",
  full_name: "Synthetic Applicant",
  email: "synthetic@example.org",
  role: "job_seeker",
  is_active: true,
  created_at: "2026-11-06T00:00:00Z",
};

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

describe("F14 owner routing", () => {
  it("opens the real feature boundary through signed-in navigation", () => {
    window.localStorage.setItem(`applywise.journey.profile.${user.id}`, JSON.stringify({
      career: "Software Engineer", focus: ["Testing"], years: "2–3 years",
      arrangement: "Hybrid", experience: "", resumeName: "",
    }));
    render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Peer review" }));
    expect(screen.getByRole("main", { name: "Peer review sharing workspace" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sharing module connected" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "New job" }));
    expect(screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" })).toBeInTheDocument();
  });
});

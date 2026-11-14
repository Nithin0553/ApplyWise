// @vitest-environment jsdom
//
// F15 is prototype-gated: `require_prototype_environment` removes its route
// when APP_ENV=production, where it answers 404. The shell must not offer an
// action the server will refuse, so the nav entry is absent in that build.
// `features/interview/availability` is the single place the two gates are kept
// in step, which is what makes this testable.
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../interview/availability", () => ({
  INTERVIEW_PREP_AVAILABLE: false,
  INTERVIEW_PREP_UNAVAILABLE:
    "Interview prep is a prototype feature and is not available in this build.",
}));
vi.mock("../sharing", () => ({ SharingPage: () => <h2>Sharing</h2> }));
vi.mock("../verification", () => ({
  VerificationPanel: () => <h2>Verification</h2>,
  listStatements: vi.fn(), submitStatement: vi.fn(),
}));
vi.mock("../review", () => ({
  StatementReviewPage: () => <h2>Review</h2>, decideStatement: vi.fn(),
}));
vi.mock("../interview", () => ({ InterviewPrepPage: () => <h2>Interview</h2> }));

import type { User } from "../auth/types";
import { GuidedJourney } from "./GuidedJourney";

const user: User = {
  id: "f15-gate-user", full_name: "Synthetic Applicant", email: "synthetic@example.com",
  role: "job_seeker", is_active: true, created_at: "2026-11-06T00:00:00Z",
};

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

describe("F15 interview prep is not offered where the route is not served", () => {
  it("omits the nav entry entirely rather than offering a broken button", () => {
    window.localStorage.setItem(`applywise.journey.profile.${user.id}`, JSON.stringify({
      career: "Software Engineer", focus: ["Testing"], years: "2–3 years",
      arrangement: "Hybrid", experience: "", resumeName: "",
    }));

    render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);

    expect(screen.queryByRole("button", { name: "Interview prep" })).not.toBeInTheDocument();
    // The other three entries are unaffected.
    expect(screen.getByRole("button", { name: "Verify claims" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review claims" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Peer review" })).toBeInTheDocument();
  });
});

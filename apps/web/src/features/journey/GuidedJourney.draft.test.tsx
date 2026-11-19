// @vitest-environment jsdom
//
// A reload used to throw away everything but the profile: the job
// description, the extracted requirements, the requirement match and the
// generated claims all lived in React state, so a refresh put the user back
// at the empty job box and every one of those had to be rebuilt with a live
// model call. These tests cover the recoverable draft, and the one thing it
// must never carry -- an F09 approval, which is a server record bound to a
// verification revision and so is re-fetched rather than restored.
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const getApprovedStatements = vi.fn();
const getEvidence = vi.fn();

vi.mock("../sharing", () => ({ SharingPage: () => <h2>Sharing</h2> }));
vi.mock("../verification", () => ({
  VerificationPanel: () => <h2>Verification</h2>,
  listStatements: vi.fn(), submitStatement: vi.fn(),
}));
vi.mock("../review", () => ({
  StatementReviewPage: () => <h2>Review</h2>, decideStatement: vi.fn(),
}));
vi.mock("../interview", () => ({ InterviewPrepPage: () => <h2>Interview</h2> }));
vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  getApprovedStatements: (...args: unknown[]) => getApprovedStatements(...args),
  getEvidence: (...args: unknown[]) => getEvidence(...args),
}));

import type { User } from "../auth/types";
import { GuidedJourney } from "./GuidedJourney";

const user: User = {
  id: "draft-user",
  full_name: "Synthetic Applicant",
  email: "synthetic@example.org",
  role: "job_seeker",
  is_active: true,
  created_at: "2026-11-15T00:00:00Z",
};

const candidate = (id: string, text: string) => ({
  statement_id: id, text, evidence_ids: ["ev-1"],
  status: "CANDIDATE" as const, verification_status: "PENDING" as const,
  approval_status: "UNREVIEWED" as const, export_eligible: false as const,
});

function seedProfile() {
  window.localStorage.setItem(`applywise.journey.profile.${user.id}`, JSON.stringify({
    career: "Systems Engineer", focus: ["Testing"], years: "2–3 years",
    arrangement: "Hybrid", experience: "", resumeName: "",
  }));
}

function seedDraft(extra: Record<string, unknown> = {}) {
  window.localStorage.setItem(`applywise.journey.draft.${user.id}`, JSON.stringify({
    stage: "resume",
    job: "Senior Systems Engineer (Angular) at Syms Strategic Group",
    role: "Senior Systems Engineer",
    company: "Syms Strategic Group",
    requirements: ["Angular 14+", "RESTful services"],
    candidates: [candidate("st-1", "Built Angular front ends for a records system.")],
    verdicts: {
      "st-1": {
        statement_id: "f08-st-1", text: "Built Angular front ends for a records system.",
        evidence_ids: ["ev-1"], status: "VERIFIED", revision: "v1-0123456789abcdef0123456789abcdef",
        findings: [], export_eligible: true,
      },
    },
    deniedIds: [],
    ...extra,
  }));
}

beforeEach(() => {
  window.localStorage.clear();
  getApprovedStatements.mockReset();
  getApprovedStatements.mockResolvedValue([]);
  getEvidence.mockReset();
  getEvidence.mockResolvedValue([]);
});
afterEach(cleanup);

describe("journey draft", () => {
  it("resumes the generated resume instead of the empty job box", async () => {
    seedProfile();
    seedDraft();
    render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);
    expect(await screen.findByText("REVIEW & APPROVAL")).toBeInTheDocument();
    expect(screen.getByText("Built Angular front ends for a records system."))
      .toBeInTheDocument();
  });

  it("asks the server which claims are approved rather than trusting the browser", async () => {
    seedProfile();
    // A browser that claims the statement is approved: the draft has no field
    // for it, and the server is the only thing consulted.
    seedDraft({ approvedIds: ["st-1"] });
    getApprovedStatements.mockResolvedValue([]);
    render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);
    await screen.findByText("REVIEW & APPROVAL");
    await waitFor(() => expect(getApprovedStatements).toHaveBeenCalledWith("synthetic-token", ["f08-st-1"]));
    // Still outstanding, because no F09 record backs it.
    expect(screen.getByText("1 line needs your review")).toBeInTheDocument();
  });

  it("restores an approval the server does confirm", async () => {
    seedProfile();
    seedDraft();
    getApprovedStatements.mockResolvedValue([{
      statement_id: "f08-st-1", text: "Built Angular front ends for a records system.",
      evidence_ids: ["ev-1"], verification_status: "VERIFIED",
    }]);
    render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);
    expect(await screen.findByText("Every line reviewed")).toBeInTheDocument();
  });


  it("ignores unrelated approval history when restoring a specific resume", async () => {
    seedProfile();
    seedDraft();
    getApprovedStatements.mockResolvedValue([{
      statement_id: "unrelated-prior-resume", text: "A different approved claim.",
      evidence_ids: ["ev-1"], verification_status: "VERIFIED",
    }]);
    render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);
    await waitFor(() => expect(getApprovedStatements).toHaveBeenCalledWith(
      "synthetic-token", ["f08-st-1"]));
    expect(screen.getByText("1 line needs your review")).toBeInTheDocument();
  });

  it("reloads the evidence a restored journey needs to cite-check the export", async () => {
    // The export checks every claim's citations against this list. A journey
    // restored without it reported the user's own approved evidence as no
    // longer approved.
    seedProfile();
    seedDraft();
    render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);
    await screen.findByText("REVIEW & APPROVAL");
    await waitFor(() => expect(getEvidence).toHaveBeenCalledWith("synthetic-token"));
  });

  it("ignores a draft parked on a transient stage", async () => {
    seedProfile();
    seedDraft({ stage: "generating" });
    render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);
    // Back to the job box, not stuck on a spinner nothing will resolve.
    expect(await screen.findByText("Continue →")).toBeInTheDocument();
    expect(screen.queryByText("REVIEW & APPROVAL")).not.toBeInTheDocument();
    expect(getApprovedStatements).not.toHaveBeenCalled();
    expect(getEvidence).not.toHaveBeenCalled();
  });
});

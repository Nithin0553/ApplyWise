// @vitest-environment jsdom
//
// TC-6 step 9: a claim stating something the approved evidence does not
// contain must not be approvable or exportable. Before F08/F09 were wired in,
// the journey's Approve button was local state and would happily accept this.
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { User } from "../auth/types";
import { GuidedJourney } from "./GuidedJourney";

const user: User = {
  id: "unsupported-test-user", full_name: "Alex Morgan", email: "alex@example.com",
  role: "job_seeker", is_active: true, created_at: "2026-10-13T00:00:00Z",
};

const evidenceId = "11111111-1111-4111-8111-111111111111";
const candidateId = "22222222-2222-4222-8222-222222222222";
const verifiedId = "44444444-4444-4444-8444-444444444444";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("an unsupported claim cannot be approved from the journey", () => {
  it("shows F08's verdict and refuses approval", async () => {
    window.localStorage.setItem(`applywise.journey.profile.${user.id}`, JSON.stringify({
      career: "QA Engineer", years: "2–3 years", arrangement: "Hybrid",
      focus: ["Testing"], experience: "Tested REST APIs.", resumeName: "",
    }));
    vi.stubGlobal("scrollTo", vi.fn());
    const decisions: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: string | URL, init?: RequestInit) => {
      const path = String(input);
      let payload: unknown;
      if (path === "/api/evidence/") {
        payload = [{ id: evidenceId, evidence_type: "work_experience", title: "API Testing",
          organization: null, role: "QA Engineer", description: "Tested REST APIs",
          status: "approved", approved_at: "2026-10-13T00:00:00Z" }];
      } else if (path.includes("/api/generation/preview")) {
        payload = { statements: [{ statement_id: candidateId,
          text: "Reduced regression runtime by 85%.", evidence_ids: [evidenceId],
          status: "CANDIDATE", verification_status: "PENDING",
          approval_status: "UNREVIEWED", export_eligible: false }] };
      } else if (path === "/api/verification/statements" && init?.method === "POST") {
        payload = { statement_id: verifiedId, text: "Reduced regression runtime by 85%.",
          evidence_ids: [evidenceId], status: "UNSUPPORTED", revision: "v1-unsupported",
          findings: [{ reason: "FIGURE_NOT_IN_EVIDENCE", detail: "85%" }],
          export_eligible: false };
      } else if (path.includes("/decision")) {
        decisions.push(path);
        payload = {};
      } else { throw Error(`Unexpected request ${path}`); }
      return { ok: true, json: async () => payload };
    }));

    render(<GuidedJourney user={user} token="test-token" logout={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" }),
      { target: { value: "QA Engineer\n- REST API testing" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue →" }));
    expect(await screen.findByRole("heading",
      { name: "Here's what the role requires." }, { timeout: 4000 })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Match with my profile/i }));
    fireEvent.click(screen.getByRole("button", { name: /Generate resume/i }));
    expect(await screen.findByRole("heading",
      { name: "Review claims before exporting" }, { timeout: 4000 })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Needs approval · Review/i }));

    // F08's reason is shown, not hidden behind a generic message. The claim
    // text also contains "85%", so assert on the verdict's own finding list.
    expect(await screen.findByText("Not supported by your evidence")).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("85%");
    expect(screen.getByText(/cannot be approved or exported/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Approve claim/ })).toBeDisabled();
    expect(decisions).toEqual([]);
    expect(screen.getByRole("button", { name: /Export reviewed resume/ })).toBeDisabled();
  }, 10000);

  it("labels the browser-side overlap estimate as not verification", async () => {
    window.localStorage.setItem(`applywise.journey.profile.${user.id}`, JSON.stringify({
      career: "QA Engineer", years: "2–3 years", arrangement: "Hybrid",
      focus: ["Testing"], experience: "Tested REST APIs.", resumeName: "",
    }));
    vi.stubGlobal("scrollTo", vi.fn());
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => [] })));

    render(<GuidedJourney user={user} token="test-token" logout={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" }),
      { target: { value: "QA Engineer\n- REST API testing" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue →" }));
    expect(await screen.findByRole("heading",
      { name: "Here's what the role requires." }, { timeout: 4000 })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Match with my profile/i }));

    expect(screen.getByText(/estimated in your browser/)).toBeInTheDocument();
    expect(screen.getByText(/This is not verification/)).toBeInTheDocument();
  }, 10000);
});

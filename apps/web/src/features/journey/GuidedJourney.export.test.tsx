// @vitest-environment jsdom
//
// The journey's export saves through POST /api/applications/reviewed-drafts,
// which stamps every statement DRAFT_USER_REVIEWED / INFERRED. F10 refuses to
// render a version whose origin is not F09_APPROVED, so that saved version can
// never be downloaded as PDF or DOCX. Two things therefore must not be claimed:
// that the saved draft is exportable, and that an approved claim is "verified"
// when F08 classified it INFERRED.
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { User } from "../auth/types";
import { GuidedJourney } from "./GuidedJourney";

const user: User = {
  id: "export-test-user", full_name: "Alex Morgan", email: "alex@example.com",
  role: "job_seeker", is_active: true, created_at: "2026-10-13T00:00:00Z",
};

const evidenceId = "11111111-1111-4111-8111-111111111111";
const candidateId = "22222222-2222-4222-8222-222222222222";
const verifiedId = "44444444-4444-4444-8444-444444444444";
const revision = "v1-0123456789abcdef0123456789abcdef";

/** A claim F08 classifies INFERRED: grounded, approvable, not certified. */
const INFERRED_CLAIM = "Improved release confidence for the billing organisation.";

/** jsdom's Blob has no text(); FileReader is what it does implement. */
function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

function persistProfile() {
  window.localStorage.setItem(`applywise.journey.profile.${user.id}`, JSON.stringify({
    career: "QA Engineer", years: "2–3 years", arrangement: "Hybrid",
    focus: ["Testing"], experience: "Tested REST APIs.", resumeName: "",
  }));
}

function stubApi() {
  return vi.fn(async (input: string | URL, init?: RequestInit) => {
    const path = String(input);
    let payload: unknown;
    if (path === "/api/evidence/") {
      payload = [{ id: evidenceId, evidence_type: "work_experience", title: "API Testing",
        organization: null, role: "QA Engineer", description: "Tested REST APIs",
        status: "approved", approved_at: "2026-10-13T00:00:00Z" }];
    } else if (path.includes("/api/generation/preview")) {
      payload = { statements: [{ statement_id: candidateId, text: INFERRED_CLAIM,
        evidence_ids: [evidenceId], status: "CANDIDATE", verification_status: "PENDING",
        approval_status: "UNREVIEWED", export_eligible: false }] };
    } else if (path === "/api/verification/statements" && init?.method === "POST") {
      payload = { statement_id: verifiedId, text: INFERRED_CLAIM,
        evidence_ids: [evidenceId], status: "INFERRED", revision,
        findings: [{ reason: "BEYOND_EVIDENCE_WORDING", detail: "40% of the claim's words appear in the evidence" }],
        export_eligible: true };
    } else if (path.includes("/decision")) {
      payload = { statement_id: verifiedId, text: INFERRED_CLAIM, evidence_ids: [evidenceId],
        verification_status: "INFERRED", verification_revision: revision,
        review_status: "APPROVED", finalization_eligible: true, reviewed_revision: revision };
    } else if (path === "/api/applications/reviewed-drafts") {
      payload = { application: { id: "33333333-3333-4333-8333-333333333333",
        role_title: "QA Engineer", company_name: "Company", status: "draft" },
        resume_version: { id: "version", version_number: 1 } };
    } else if (path === "/api/applications/") {
      payload = [{ id: "33333333-3333-4333-8333-333333333333",
        role_title: "QA Engineer", company_name: "Company", status: "draft" }];
    } else if (path === "/api/applications/resume-version-counts") {
      payload = { "33333333-3333-4333-8333-333333333333": 1 };
    } else { throw Error(`Unexpected request ${path}`); }
    return { ok: true, json: async () => payload };
  });
}

async function reachReviewStage() {
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
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("the journey does not overstate what its saved draft is", () => {
  it("does not promise PDF or Word export for a historical draft", async () => {
    persistProfile();
    vi.stubGlobal("scrollTo", vi.fn());
    vi.stubGlobal("fetch", stubApi());

    await reachReviewStage();

    expect(screen.getByText(/not eligible for PDF or Word export/)).toBeInTheDocument();
    expect(screen.queryByText(/can be exported as PDF or Word/)).not.toBeInTheDocument();
  }, 10000);

  it("keeps an approved INFERRED claim labelled INFERRED in the downloaded file", async () => {
    persistProfile();
    vi.stubGlobal("scrollTo", vi.fn());
    vi.stubGlobal("fetch", stubApi());
    let downloaded: Blob | null = null;
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn((blob: Blob) => { downloaded = blob; return "blob:test"; }),
    });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await reachReviewStage();
    fireEvent.click(screen.getByRole("button", { name: /Needs approval · Review/i }));
    // INFERRED is approvable: only UNSUPPORTED is barred.
    const approve = screen.getByRole("button", { name: /Approve claim/ });
    expect(approve).not.toBeDisabled();
    fireEvent.click(approve);
    await waitFor(() => expect(
      screen.queryByRole("button", { name: /Needs approval · Review/i })).not.toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Export reviewed resume/ }));

    await waitFor(() => expect(downloaded).not.toBeNull(), { timeout: 4000 });
    const text = await readBlob(downloaded as unknown as Blob);
    expect(text).toContain("[inferred: grounded, not certified]");
    expect(text).toContain("Inferred claims are grounded but not certified.");
    expect(text).toContain("This file is not a trusted export.");
    // The blanket claim this replaced must not come back.
    expect(text).not.toContain("Verified against the author's own approved evidence");
    expect(text).not.toContain("[verified against cited evidence]");
  }, 15000);
});

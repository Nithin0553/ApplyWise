// @vitest-environment jsdom
//
// F08, F09 and F15 each shipped a finished page that nothing outside its own
// folder imported, so none of them had a click path and the STD cases covering
// them could not be executed through the UI. These tests fail if that
// regresses: they reach each page the way a signed-in user does, through the
// workspace navigation.
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const listStatements = vi.fn();
const getApprovedStatements = vi.fn();
// What the shell actually hands VerificationPanel, so an empty evidence
// list cannot pass as "the page rendered".
const panelProps: Array<{ evidenceIds?: string[] }> = [];

vi.mock("../sharing", () => ({ SharingPage: () => <h2>Sharing module connected</h2> }));
vi.mock("../verification", () => ({
  VerificationPanel: (props: { evidenceIds?: string[] }) => {
    panelProps.push(props);
    return <h2>Verification module connected</h2>;
  },
  listStatements: (...args: unknown[]) => listStatements(...args),
}));
vi.mock("../review", () => ({
  StatementReviewPage: ({ statementId }: { statementId: string }) =>
    <h2>Review module connected for {statementId}</h2>,
}));
vi.mock("../interview", () => ({
  InterviewPrepPage: ({ statements }: { statements: unknown[] }) =>
    <h2>Interview module connected with {statements.length} statements</h2>,
}));
vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  getApprovedStatements: (...args: unknown[]) => getApprovedStatements(...args),
}));

import type { User } from "../auth/types";
import { GuidedJourney } from "./GuidedJourney";

const user: User = {
  id: "reachability-user",
  full_name: "Synthetic Applicant",
  email: "synthetic@example.org",
  role: "job_seeker",
  is_active: true,
  created_at: "2026-11-06T00:00:00Z",
};

function renderSignedIn() {
  window.localStorage.setItem(`applywise.journey.profile.${user.id}`, JSON.stringify({
    career: "Software Engineer", focus: ["Testing"], years: "2–3 years",
    arrangement: "Hybrid", experience: "", resumeName: "",
  }));
  render(<GuidedJourney user={user} token="synthetic-token" logout={vi.fn()} />);
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  listStatements.mockReset();
  getApprovedStatements.mockReset();
  panelProps.length = 0;
  vi.unstubAllGlobals();
});

describe("feature pages are reachable from the workspace navigation", () => {
  it("opens F08 claim verification", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => [] })));
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Verify claims" }));

    expect(await screen.findByRole("main", { name: "Claim verification workspace" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Verification module connected" })).toBeInTheDocument();
  });

  it("loads approved evidence on entry for a user who signs in and goes straight there", async () => {
    // Regression: `evidence` was only populated by analyzeJob(), so opening
    // Verify claims first handed the panel an empty citable-evidence list and
    // its Add button stayed disabled even with approved F02 records.
    const approvedId = "11111111-1111-4111-8111-111111111111";
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => [
        { id: approvedId, evidence_type: "work_experience", title: "API Testing",
          organization: null, role: "QA Engineer", description: "Tested REST APIs",
          status: "approved", approved_at: "2026-11-01T00:00:00Z" },
        { id: "22222222-2222-4222-8222-222222222222", evidence_type: "project",
          title: "Unconfirmed", organization: null, role: null, description: null,
          status: "unconfirmed", approved_at: null },
      ],
    }));
    vi.stubGlobal("fetch", fetchMock);
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Verify claims" }));

    expect(await screen.findByRole("main", { name: "Claim verification workspace" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/evidence/", expect.objectContaining({
      headers: expect.any(Headers),
    }));
    // Only the approved record is citable; the unconfirmed one is excluded.
    expect(panelProps.at(-1)?.evidenceIds).toEqual([approvedId]);
  });

  it("surfaces a failure to load evidence instead of an empty panel", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false, status: 401, json: async () => ({ detail: "Session expired." }),
    })));
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Verify claims" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Session expired.");
  });

  it("offers Interview prep while the F15 prototype route is served", () => {
    renderSignedIn();

    expect(screen.getByRole("button", { name: "Interview prep" })).toBeInTheDocument();
  });

  it("opens F09 review and reaches one claim's review from the list", async () => {
    listStatements.mockResolvedValue([
      { statement_id: "claim-1", text: "Built automated regression suites", evidence_ids: [],
        status: "VERIFIED", revision: "v1-abc", findings: [], export_eligible: true },
    ]);
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Review claims" }));

    expect(await screen.findByRole("main", { name: "Statement review workspace" })).toBeInTheDocument();
    const claim = await screen.findByRole("button", { name: /Built automated regression suites/ });
    fireEvent.click(claim);
    expect(await screen.findByRole("heading", { name: "Review module connected for claim-1" }))
      .toBeInTheDocument();
    expect(listStatements).toHaveBeenCalledWith("synthetic-token");
  });

  it("tells the user when no claims have been submitted yet", async () => {
    listStatements.mockResolvedValue([]);
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Review claims" }));

    expect(await screen.findByText(/No claims submitted yet/)).toBeInTheDocument();
  });

  it("opens F15 interview prep with the statements F09 reports as approved", async () => {
    // Server-authoritative: the shell must not assemble this list itself.
    getApprovedStatements.mockResolvedValue([
      { statement_id: "claim-1", text: "Built automated regression suites",
        evidence_ids: ["e1"], verification_status: "VERIFIED" },
    ]);
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Interview prep" }));

    expect(await screen.findByRole("heading", { name: /Interview module connected with 1 statements/ }))
      .toBeInTheDocument();
    expect(getApprovedStatements).toHaveBeenCalledWith("synthetic-token");
  });

  it("surfaces a load failure instead of showing an empty page", async () => {
    listStatements.mockRejectedValue(new Error("Session expired."));
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Review claims" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Session expired.");
  });
});

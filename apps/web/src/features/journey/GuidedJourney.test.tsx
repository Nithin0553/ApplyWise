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
  it("requires human approval, persists a resume version, and downloads only approved text", async () => {
    window.localStorage.setItem(
      `applywise.journey.profile.${user.id}`,
      JSON.stringify({ career: "QA Engineer", years: "3–5 years", arrangement: "Hybrid",
        focus: ["Testing"], experience: "Tested REST APIs.", resumeName: "" }),
    );
    vi.stubGlobal("scrollTo", vi.fn());
    const evidenceId = "11111111-1111-4111-8111-111111111111";
    const statementId = "22222222-2222-4222-8222-222222222222";
    const requests: string[] = [];
    const fetchMock = vi.fn(async (input: string | URL, init?: RequestInit) => {
      const path = String(input);
      requests.push(path);
      let payload: unknown;
      if (path === "/api/evidence/") {
        payload = [{ id: evidenceId, evidence_type: "work_experience", title: "API Testing",
          organization: null, role: "QA Engineer", description: "Tested REST APIs",
          status: "approved", approved_at: "2026-10-13T00:00:00Z" }];
      } else if (path.includes("/api/generation/preview")) {
        payload = { statements: [{ statement_id: statementId, text: "Tested REST APIs.",
          evidence_ids: [evidenceId], status: "CANDIDATE", verification_status: "PENDING",
          approval_status: "UNREVIEWED", export_eligible: false }] };
      } else if (path === "/api/applications/" && init?.method === "POST") {
        payload = { id: "33333333-3333-4333-8333-333333333333", role_title: "QA Engineer",
          company_name: "Company", status: "draft", created_at: "2026-10-13T00:00:00Z" };
      } else if (path.includes("resume-versions") && init?.method === "POST") {
        const posted = JSON.parse(String(init.body)) as { statements: Array<{ text: string; approval_status: string }> };
        expect(posted.statements).toEqual([expect.objectContaining({
          text: "Tested REST APIs.", approval_status: "APPROVED",
          verification_status: "INFERRED",
        })]);
        payload = { id: "version", version_number: 1 };
      } else if (path === "/api/applications/") {
        payload = [{ id: "33333333-3333-4333-8333-333333333333",
          role_title: "QA Engineer", company_name: "Company", status: "draft" }];
      } else if (path.includes("resume-versions")) {
        payload = [{ id: "version", version_number: 1 }];
      } else { throw Error(`Unexpected request ${path}`); }
      return { ok: true, json: async () => payload };
    });
    vi.stubGlobal("fetch", fetchMock);
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:reviewed") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    render(<GuidedJourney user={user} token="test-token" logout={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" }),
      { target: { value: "QA Engineer\\n- REST API testing" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue →" }));
    expect(await screen.findByRole("heading", { name: "Here's what the role asks for." }, { timeout: 4000 })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Generate resume/i }));
    expect(await screen.findByRole("heading", { name: "Make every line yours." }, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Save to applications/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Review this line/i }));
    expect(screen.getByText(/Tested REST APIs/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /I verified this — Approve/ }));
    expect(screen.queryByRole("button", { name: /Review this line/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Save to applications/ }));
    expect(await screen.findByRole("heading", { name: "Applications" }, { timeout: 6000 })).toBeInTheDocument();
    expect(requests).toContain("/api/applications/");
    expect(requests.some((path) => path.includes("resume-versions"))).toBe(true);
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    vi.restoreAllMocks();
  }, 10000);

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

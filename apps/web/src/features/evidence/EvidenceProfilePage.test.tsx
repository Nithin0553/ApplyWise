// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvidenceManager } from "./EvidenceProfilePage";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const UNCONFIRMED = {
  id: "11111111-1111-1111-1111-111111111111",
  user_id: "22222222-2222-2222-2222-222222222222",
  evidence_type: "project",
  title: "ApplyWise capstone",
  organization: "Team Islanders",
  role: "Project Manager",
  location: null,
  description: "Coordinated an evidence-grounded career assistant project.",
  skill_name: null,
  proficiency: null,
  credential: null,
  url: null,
  start_date: "2026-09-01",
  end_date: null,
  source: "Manual entry",
  status: "unconfirmed",
  approved_at: null,
  created_at: "2026-10-05T12:00:00Z",
  updated_at: "2026-10-05T12:00:00Z",
};

const APPROVED = {
  ...UNCONFIRMED,
  status: "approved",
  approved_at: "2026-10-05T13:00:00Z",
  updated_at: "2026-10-05T13:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("EvidenceManager", () => {
  it("loads evidence and approves an unconfirmed record", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/evidence/") && (!init?.method || init.method === "GET")) {
        return jsonResponse([UNCONFIRMED]);
      }
      if (url.endsWith(`/api/evidence/${UNCONFIRMED.id}/approve`) && init?.method === "POST") {
        return jsonResponse(APPROVED);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<EvidenceManager token="opaque-token" />);

    expect(await screen.findByText("ApplyWise capstone")).toBeInTheDocument();
    expect(screen.getByText("Unconfirmed")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Approve evidence" }));

    expect(await screen.findByText("Approved")).toBeInTheDocument();
    expect(screen.getByText(/can be used for grounded generation/i)).toBeInTheDocument();

    const approveCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith(`/api/evidence/${UNCONFIRMED.id}/approve`),
    );
    expect(approveCall).toBeDefined();
    const approveHeaders = new Headers(approveCall?.[1]?.headers);
    expect(approveHeaders.get("Authorization")).toBe("Bearer opaque-token");
  });

  it("shows the approved-edit warning before saving changes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([APPROVED]));
    vi.stubGlobal("fetch", fetchMock);

    render(<EvidenceManager token="opaque-token" />);

    expect(await screen.findByText("ApplyWise capstone")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByRole("note")).toHaveTextContent("return it to unconfirmed status");
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument();
  });
});

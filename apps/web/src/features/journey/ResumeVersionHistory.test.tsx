// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  getVersions: vi.fn(),
}));

import { getVersions, type JourneyResumeVersion } from "./api";
import { ResumeVersionHistory } from "./ResumeVersionHistory";

const applicationId = "11111111-1111-4111-8111-111111111111";
const sourceId = "22222222-2222-4222-8222-222222222222";

function statement(id: string, text: string) {
  return {
    statement_id: id,
    text,
    evidence_ids: [sourceId],
    verification_status: "INFERRED" as const,
    approval_status: "APPROVED" as const,
    origin: "DRAFT_USER_REVIEWED" as const,
  };
}

const versions: JourneyResumeVersion[] = [
  {
    id: "version-one", version_number: 1, created_at: "2026-10-20T12:00:00Z",
    snapshot: { statements: [
      statement("old-1", "Built REST APIs in Python."),
      statement("old-2", "Worked with legacy databases."),
    ] },
  },
  {
    id: "version-two", version_number: 2, created_at: "2026-10-22T12:00:00Z",
    snapshot: { statements: [
      statement("new-1", "Built REST APIs in Python."),
      statement("new-2", "Added automated API tests."),
    ] },
  },
];

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("F13 read-only version history", () => {
  it("fetches owned versions only when opened and displays the latest saved snapshot", async () => {
    vi.mocked(getVersions).mockResolvedValue(versions);
    render(<ResumeVersionHistory token="synthetic-token" applicationId={applicationId} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading saved versions");
    expect(await screen.findByText("Added automated API tests.")).toBeInTheDocument();
    expect(getVersions).toHaveBeenCalledTimes(1);
    expect(getVersions).toHaveBeenCalledWith("synthetic-token", applicationId);
    expect(screen.getByText("Resume version 2")).toBeInTheDocument();
    expect(screen.getAllByText("DRAFT_USER_REVIEWED")).toHaveLength(2);
    expect(screen.getByText(/not an export approval/i)).toBeInTheDocument();
  });

  it("compares immutable statement text instead of regenerated IDs", async () => {
    vi.mocked(getVersions).mockResolvedValue(versions);
    render(<ResumeVersionHistory token="synthetic-token" applicationId={applicationId} />);
    await screen.findByText("Added automated API tests.");
    fireEvent.change(screen.getByRole("combobox", { name: "Compare with resume version" }), {
      target: { value: "version-one" },
    });
    expect(screen.getByText("1 added, 1 removed, 1 unchanged.")).toBeInTheDocument();
    expect(screen.getByText("Statements only in version 1")).toBeInTheDocument();
    expect(screen.getByText("Worked with legacy databases.")).toBeInTheDocument();
    expect(screen.getByText(/exact statement wording after whitespace normalization/)).toBeInTheDocument();
  });

  it("can view older versions without changing any backend records", async () => {
    vi.mocked(getVersions).mockResolvedValue(versions);
    render(<ResumeVersionHistory token="synthetic-token" applicationId={applicationId} />);
    await screen.findByText("Added automated API tests.");
    fireEvent.change(screen.getByRole("combobox", { name: "View resume version" }), {
      target: { value: "version-one" },
    });
    expect(screen.getByText("Resume version 1")).toBeInTheDocument();
    expect(screen.getByText("Worked with legacy databases.")).toBeInTheDocument();
    expect(getVersions).toHaveBeenCalledTimes(1);
  });

  it("handles an empty application history", async () => {
    vi.mocked(getVersions).mockResolvedValue([]);
    render(<ResumeVersionHistory token="synthetic-token" applicationId={applicationId} />);
    expect(await screen.findByText("No saved resume versions for this application yet.")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("reports load errors and allows retry without claiming success", async () => {
    vi.mocked(getVersions).mockRejectedValueOnce(new Error("Version history unavailable"))
      .mockResolvedValueOnce(versions);
    render(<ResumeVersionHistory token="synthetic-token" applicationId={applicationId} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Version history unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Retry loading versions" }));
    expect(await screen.findByText("Added automated API tests.")).toBeInTheDocument();
    await waitFor(() => expect(getVersions).toHaveBeenCalledTimes(2));
  });
});

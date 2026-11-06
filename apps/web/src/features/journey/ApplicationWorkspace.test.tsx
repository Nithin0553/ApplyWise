// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApplicationWorkspace } from "./ApplicationWorkspace";
import type { JourneyApplication } from "./api";

const base: JourneyApplication = {
  id: "11111111-1111-4111-8111-111111111111",
  company_name: "Example Company",
  role_title: "Software Engineer",
  status: "draft",
  notes: "Initial draft",
  job_url: null,
  next_action_on: null,
  applied_on: null,
  created_at: "2026-10-31T12:00:00Z",
};
const renderWorkspace = (items: JourneyApplication[] = [base], onChange = vi.fn()) => {
  render(<ApplicationWorkspace token="test-token" applications={items}
    versionCounts={{ [base.id]: 2 }} onChange={onChange}
    onNewJob={vi.fn()} onEditProfile={vi.fn()} />);
  return onChange;
};

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("F13 application workspace", () => {
  it("renders real application counts and exposes details without changing snapshots", () => {
    renderWorkspace();
    expect(screen.getByRole("heading", { name: "My Applications" })).toBeInTheDocument();
    expect(screen.getByText("Software Engineer")).toBeInTheDocument();
    expect(screen.getByText("2 resume versions")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Manage" }));
    expect(screen.getByLabelText("Job posting URL")).toBeInTheDocument();
    expect(screen.getByLabelText("Next action date")).toBeInTheDocument();
    expect(screen.getByLabelText("Notes")).toHaveValue("Initial draft");
    expect(screen.getByText(/Historical resume snapshots are never changed/)).toBeInTheDocument();
  });

  it("loads immutable version history only after a user requests it", async () => {
    const id = "123e4567-e89b-42d3-a456-426614174000";
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => [{
        id: "stored-v1", version_number: 1, created_at: "2026-11-06T12:00:00Z",
        snapshot: { statements: [{
          statement_id: id,
          text: "Built a synthetic workflow.",
          evidence_ids: ["evidence-id"],
          verification_status: "INFERRED", approval_status: "APPROVED",
          origin: "DRAFT_USER_REVIEWED",
        }] },
      }],
    }));
    vi.stubGlobal("fetch", fetchMock);
    renderWorkspace();
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Manage" }));
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "View resume history" }));
    expect(await screen.findByText("Built a synthetic workflow.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/applications/${base.id}/resume-versions`,
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Hide resume history" }));
    expect(screen.queryByText("Built a synthetic workflow.")).not.toBeInTheDocument();
  });

  it("saves job link, follow-up date and notes through the owned F13 PATCH endpoint", async () => {
    const updated = {
      ...base, job_url: "https://example.org/jobs/123", next_action_on: "2026-12-01", notes: "Contact recruiter",
    };
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => updated }));
    vi.stubGlobal("fetch", fetchMock);
    const onChange = renderWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "Manage" }));
    fireEvent.change(screen.getByLabelText("Job posting URL"), { target: { value: "https://example.org/jobs/123" } });
    fireEvent.change(screen.getByLabelText("Next action date"), { target: { value: "2026-12-01" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Contact recruiter" } });
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(updated));
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/applications/${base.id}`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          notes: "Contact recruiter", job_url: "https://example.org/jobs/123", next_action_on: "2026-12-01",
        }),
      }),
    );
  });

  it("transitions through a valid application lifecycle using the status endpoint", async () => {
    const updated = { ...base, status: "applied", applied_on: "2026-11-05" };
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => updated }));
    vi.stubGlobal("fetch", fetchMock);
    const onChange = renderWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "Manage" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Change status for Software Engineer" }),
      { target: { value: "applied" } });
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(updated));
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/applications/${base.id}/status`,
      expect.objectContaining({ method: "POST", body: JSON.stringify({ status: "applied" }) }),
    );
  });

  it("does not offer invalid reopen transitions for a terminal status", () => {
    renderWorkspace([{ ...base, status: "accepted" }]);
    fireEvent.click(screen.getByRole("button", { name: "Manage" }));
    expect(screen.queryByRole("combobox", { name: "Change status for Software Engineer" })).not.toBeInTheDocument();
    expect(screen.getByText(/Reopening is not supported/)).toBeInTheDocument();
  });

  it("shows failed API changes as errors without claiming a save", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false, status: 409, json: async () => ({ detail: "Invalid status transition" }),
    })));
    const onChange = renderWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "Manage" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Change status for Software Engineer" }),
      { target: { value: "applied" } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid status transition");
    expect(onChange).not.toHaveBeenCalled();
  });
});

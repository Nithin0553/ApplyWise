// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApplicationApiRecord, ResumeVersionApiRecord } from "./api";

const apiMocks = vi.hoisted(() => ({
  listApplications: vi.fn(),
  listResumeVersions: vi.fn(),
  createApplication: vi.fn(),
  updateApplication: vi.fn(),
  transitionApplicationStatus: vi.fn(),
  getResumeVersion: vi.fn(),
}));

vi.mock("../auth", () => ({
  useAuth: () => ({ token: "session-token" }),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, ...apiMocks };
});

import { ApplicationsPage } from "./ApplicationsPage";

const applicationRecord: ApplicationApiRecord = {
  id: "app-1",
  user_id: "user-1",
  company_name: "Example Robotics",
  role_title: "Software Engineer",
  location: "Dallas, TX",
  job_url: "https://example.invalid/jobs/1",
  source: "Career fair",
  notes: "Follow up",
  status: "applied",
  applied_on: "2026-10-01",
  next_action_on: "2026-10-08",
  closed_on: null,
  created_at: "2026-10-01T12:00:00Z",
  updated_at: "2026-10-02T12:00:00Z",
};

const resumeVersion: ResumeVersionApiRecord = {
  id: "version-1",
  user_id: "user-1",
  application_id: "app-1",
  version_number: 1,
  created_at: "2026-10-02T12:00:00Z",
  snapshot: {
    user_id: "user-1",
    application_id: "app-1",
    resume_version_id: "version-1",
    created_at: "2026-10-02T12:00:00Z",
    evidence: [],
    statements: [
      {
        statement_id: "statement-1",
        text: "Built a synthetic regression suite.",
        evidence_ids: [],
        verification_status: "VERIFIED",
        approval_status: "APPROVED",
      },
    ],
  },
};

beforeEach(() => {
  apiMocks.listApplications.mockResolvedValue([applicationRecord]);
  apiMocks.listResumeVersions.mockResolvedValue([resumeVersion]);
  apiMocks.createApplication.mockResolvedValue(applicationRecord);
  apiMocks.updateApplication.mockResolvedValue(applicationRecord);
  apiMocks.transitionApplicationStatus.mockResolvedValue(applicationRecord);
  apiMocks.getResumeVersion.mockResolvedValue(resumeVersion);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ApplicationsPage", () => {
  it("loads owner-scoped applications and opens an immutable resume snapshot", async () => {
    render(<ApplicationsPage />);

    expect(
      await screen.findByRole("heading", { name: "Example Robotics" }),
    ).toBeInTheDocument();
    expect(apiMocks.listApplications).toHaveBeenCalledWith("session-token");
    expect(apiMocks.listResumeVersions).toHaveBeenCalledWith("session-token", "app-1");

    fireEvent.click(screen.getByRole("button", { name: /Version 1/ }));

    expect(apiMocks.getResumeVersion).toHaveBeenCalledWith("session-token", "version-1");
    expect(
      await screen.findByRole("heading", { name: "Resume version 1" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Built a synthetic regression suite.")).toBeInTheDocument();
  });

  it("creates an application through the authenticated F13 client", async () => {
    render(<ApplicationsPage />);
    await screen.findByRole("heading", { name: "Example Robotics" });

    fireEvent.click(screen.getByRole("button", { name: "Add application" }));
    fireEvent.change(screen.getByLabelText("Company"), {
      target: { value: "Synthetic Systems" },
    });
    fireEvent.change(screen.getByLabelText("Role title"), {
      target: { value: "Backend Engineer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save application" }));

    await waitFor(() =>
      expect(apiMocks.createApplication).toHaveBeenCalledWith(
        "session-token",
        expect.objectContaining({
          companyName: "Synthetic Systems",
          roleTitle: "Backend Engineer",
        }),
      ),
    );
  });
});

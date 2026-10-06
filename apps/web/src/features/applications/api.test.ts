// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createApplication,
  listApplications,
  saveResumeVersion,
  toApplicationFormValues,
  toApplicationSummary,
  toResumeVersionSummary,
  transitionApplicationStatus,
  type ApplicationApiRecord,
  type ResumeVersionApiRecord,
  type ResumeVersionContent,
} from "./api";

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
  version_number: 2,
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

afterEach(() => {
  vi.restoreAllMocks();
});

describe("applications api", () => {
  it("authenticates list requests with the F01 bearer token", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([applicationRecord]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(listApplications("session-token")).resolves.toEqual([applicationRecord]);

    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer session-token");
  });

  it("maps create form values to the backend snake-case contract", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(applicationRecord), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await createApplication("session-token", {
      companyName: " Example Robotics ",
      roleTitle: " Software Engineer ",
      location: " ",
      jobUrl: "https://example.invalid/jobs/1",
      source: "Career fair",
      notes: " Follow up ",
      appliedOn: "2026-10-01",
      nextActionOn: "2026-10-08",
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(String(init?.body))).toEqual({
      company_name: "Example Robotics",
      role_title: "Software Engineer",
      location: null,
      job_url: "https://example.invalid/jobs/1",
      source: "Career fair",
      notes: "Follow up",
      applied_on: "2026-10-01",
      next_action_on: "2026-10-08",
    });
  });

  it("uses the dedicated status transition endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ...applicationRecord, status: "interviewing" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await transitionApplicationStatus("session-token", "app-1", "interviewing");

    expect(fetchMock.mock.calls[0][0]).toContain("/api/applications/app-1/status");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      status: "interviewing",
    });
  });

  it("saves only immutable resume content and leaves owner/version identity to the backend", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(resumeVersion), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const content: ResumeVersionContent = {
      evidence: [
        {
          evidence_id: "evidence-1",
          evidence_type: "project",
          title: "Synthetic project",
          organization: null,
          role: "Developer",
          description: "Built a synthetic regression suite.",
          approved_at: "2026-10-01T10:00:00Z",
        },
      ],
      statements: [
        {
          statement_id: "statement-1",
          text: "Built a synthetic regression suite.",
          evidence_ids: ["evidence-1"],
          verification_status: "VERIFIED",
          approval_status: "APPROVED",
        },
      ],
    };

    await saveResumeVersion("session-token", "app-1", content);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/applications/app-1/resume-versions");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual(content);
    expect(String(init?.body)).not.toContain("user_id");
    expect(String(init?.body)).not.toContain("resume_version_id");
  });

  it("maps backend records into the existing presentation contracts", () => {
    expect(toApplicationSummary(applicationRecord, 2)).toMatchObject({
      id: "app-1",
      companyName: "Example Robotics",
      roleTitle: "Software Engineer",
      status: "applied",
      versionCount: 2,
    });
    expect(toApplicationFormValues(applicationRecord)).toMatchObject({
      companyName: "Example Robotics",
      jobUrl: "https://example.invalid/jobs/1",
      notes: "Follow up",
    });
    expect(toResumeVersionSummary(resumeVersion)).toEqual({
      id: "version-1",
      versionNumber: 2,
      createdAt: "2026-10-02T12:00:00Z",
      statementCount: 1,
    });
  });
});

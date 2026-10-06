// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  listOwnedShares: vi.fn(),
  listShareableResumeVersions: vi.fn(),
  listPeerFeedback: vi.fn(),
  createShare: vi.fn(),
  revokeShare: vi.fn(),
  resolveShare: vi.fn(),
  submitPeerFeedback: vi.fn(),
}));

vi.mock("../auth", () => ({ useAuth: mocks.useAuth }));
vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return {
    ...actual,
    listOwnedShares: mocks.listOwnedShares,
    listShareableResumeVersions: mocks.listShareableResumeVersions,
    listPeerFeedback: mocks.listPeerFeedback,
    createShare: mocks.createShare,
    revokeShare: mocks.revokeShare,
    resolveShare: mocks.resolveShare,
    submitPeerFeedback: mocks.submitPeerFeedback,
  };
});

import { ReviewerSharePage } from "./ReviewerSharePage";
import { SharingPage } from "./SharingPage";

const grant = {
  id: "share-1",
  owner_user_id: "owner-1",
  resume_version_id: "version-1",
  expires_at: null,
  revoked_at: null,
  created_at: "2026-10-06T12:00:00Z",
};

beforeEach(() => {
  mocks.useAuth.mockReturnValue({ token: "synthetic-token" });
  mocks.listOwnedShares.mockResolvedValue([grant]);
  mocks.listShareableResumeVersions.mockResolvedValue([
    {
      id: "version-1",
      applicationId: "app-1",
      versionNumber: 1,
      createdAt: "2026-10-05T12:00:00Z",
      label: "Synthetic Labs — Engineer — Resume v1",
    },
  ]);
  mocks.listPeerFeedback.mockResolvedValue([
    {
      id: "feedback-1",
      share_id: "share-1",
      resume_version_id: "version-1",
      reviewer_user_id: "reviewer-1",
      comment: "Strong evidence chain.",
      created_at: "2026-10-06T13:00:00Z",
    },
  ]);
  mocks.createShare.mockResolvedValue({
    grant,
    secret: "synthetic-share-secret-123456",
  });
  mocks.revokeShare.mockResolvedValue({ ...grant, revoked_at: "2026-10-06T14:00:00Z" });
  mocks.resolveShare.mockResolvedValue({
    share_id: "share-1",
    resume_version_id: "version-1-12345678",
    created_at: "2026-10-06T12:00:00Z",
    expires_at: null,
  });
  mocks.submitPeerFeedback.mockResolvedValue({
    id: "feedback-new",
    share_id: "share-1",
    resume_version_id: "version-1-12345678",
    reviewer_user_id: "reviewer-1",
    comment: "Keep the quantified result.",
    created_at: "2026-10-06T15:00:00Z",
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SharingPage", () => {
  it("loads owner shares, creates a link, and opens read-only feedback", async () => {
    render(<SharingPage />);

    expect(
      await screen.findByRole("heading", { name: "Peer review sharing" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Synthetic Labs — Engineer — Resume v1")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "View feedback" }));
    expect(await screen.findByText("Strong evidence chain.")).toBeInTheDocument();
    expect(mocks.listPeerFeedback).toHaveBeenCalledWith("synthetic-token", "share-1");

    fireEvent.click(screen.getByRole("button", { name: "Create share link" }));
    await waitFor(() => {
      expect(mocks.createShare).toHaveBeenCalledWith(
        "synthetic-token",
        "version-1",
        null,
      );
    });
    const newShareLink = (await screen.findByLabelText("New share link")) as HTMLInputElement;
    expect(newShareLink.value).toContain("share=synthetic-share-secret-123456");
  });
});

describe("ReviewerSharePage", () => {
  it("resolves only the supplied secret and submits feedback through the reviewer endpoint", async () => {
    const secret = "synthetic-share-secret-123456";
    render(<ReviewerSharePage secret={secret} />);

    expect(await screen.findByText("version-1-12345678")).toBeInTheDocument();
    expect(mocks.resolveShare).toHaveBeenCalledWith("synthetic-token", secret);

    fireEvent.change(screen.getByLabelText("Feedback"), {
      target: { value: "  Keep the quantified result.  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    await waitFor(() => {
      expect(mocks.submitPeerFeedback).toHaveBeenCalledWith(
        "synthetic-token",
        secret,
        "Keep the quantified result.",
      );
    });
    expect(await screen.findByText("Keep the quantified result.")).toBeInTheDocument();
  });
});

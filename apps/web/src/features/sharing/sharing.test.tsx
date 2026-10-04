// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PeerFeedbackPanel } from "./PeerFeedbackPanel";
import { ShareManager } from "./ShareManager";
import type { PeerFeedbackSummary, ShareGrantSummary } from "./types";

afterEach(cleanup);

const now = new Date("2026-10-01T12:00:00Z");

const shares: readonly ShareGrantSummary[] = [
  {
    id: "share-active",
    resumeVersionId: "version-1",
    resumeVersionLabel: "Resume version 1",
    createdAt: "2026-09-30T12:00:00Z",
    expiresAt: "2026-10-02T12:00:00Z",
  },
  {
    id: "share-expired",
    resumeVersionId: "version-2",
    resumeVersionLabel: "Resume version 2",
    createdAt: "2026-09-20T12:00:00Z",
    expiresAt: "2026-09-30T12:00:00Z",
  },
  {
    id: "share-revoked",
    resumeVersionId: "version-3",
    resumeVersionLabel: "Resume version 3",
    createdAt: "2026-09-25T12:00:00Z",
    revokedAt: "2026-09-29T12:00:00Z",
  },
];

const feedback: readonly PeerFeedbackSummary[] = [
  {
    id: "feedback-1",
    reviewerLabel: "Reviewer",
    comment: "Clarify the synthetic outcome.",
    createdAt: "2026-10-01T10:00:00Z",
  },
];

describe("ShareManager", () => {
  it("shows share lifecycle state without reopening inactive shares", () => {
    const onRevokeShare = vi.fn();

    render(
      <ShareManager shares={shares} now={now} onRevokeShare={onRevokeShare} />,
    );

    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Expired")).toBeInTheDocument();
    expect(screen.getByText("Revoked")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Revoke Resume version 1" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Revoke Resume version 2" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Revoke Resume version 3" }),
    ).not.toBeInTheDocument();
  });

  it("emits create, copy, and revoke actions to its parent", () => {
    const onCreateShare = vi.fn();
    const onCopyShareUrl = vi.fn();
    const onRevokeShare = vi.fn();
    const shareUrl = "https://example.invalid/review/synthetic-secret";

    render(
      <ShareManager
        shares={shares}
        newShareUrl={shareUrl}
        now={now}
        onCreateShare={onCreateShare}
        onCopyShareUrl={onCopyShareUrl}
        onRevokeShare={onRevokeShare}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create share link" }));
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Revoke Resume version 1" }),
    );

    expect(onCreateShare).toHaveBeenCalledTimes(1);
    expect(onCopyShareUrl).toHaveBeenCalledWith(shareUrl);
    expect(onRevokeShare).toHaveBeenCalledWith("share-active");
  });
});

describe("PeerFeedbackPanel", () => {
  it("renders existing feedback and submits normalized new feedback", () => {
    const onSubmitFeedback = vi.fn();

    render(
      <PeerFeedbackPanel
        resumeVersionLabel="Resume version 1"
        feedback={feedback}
        onSubmitFeedback={onSubmitFeedback}
      />,
    );

    expect(screen.getByText("Clarify the synthetic outcome.")).toBeInTheDocument();

    const textarea = screen.getByLabelText("Feedback");
    fireEvent.change(textarea, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));
    expect(onSubmitFeedback).not.toHaveBeenCalled();

    fireEvent.change(textarea, {
      target: { value: "  Strong synthetic structure.  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    expect(onSubmitFeedback).toHaveBeenCalledWith("Strong synthetic structure.");
    expect(textarea).toHaveValue("");
  });

  it("supports a read-only owner view by omitting the submission form", () => {
    render(
      <PeerFeedbackPanel
        resumeVersionLabel="Resume version 1"
        feedback={feedback}
      />,
    );

    expect(
      screen.queryByRole("button", { name: "Submit feedback" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Clarify the synthetic outcome.")).toBeInTheDocument();
  });
});

// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  readStatementReview: vi.fn(),
  readReviewHistory: vi.fn(),
  decideStatement: vi.fn(),
}));

import { decideStatement, readReviewHistory, readStatementReview } from "./api";
import { StatementReviewPage } from "./StatementReviewPage";

const statementId = "11111111-1111-4111-8111-111111111111";
const payload = {
  statement_id: statementId,
  text: "Built REST API tests in Python.",
  evidence_ids: ["22222222-2222-4222-8222-222222222222"],
  verification_status: "VERIFIED" as const,
  verification_revision: "version-one-verified",
  review_status: "UNREVIEWED" as const,
  finalization_eligible: false,
  reviewed_revision: null,
};

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("F09 standalone reviewed-statement panel", () => {
  it("uses authoritative current revision rather than forged text or status", async () => {
    vi.mocked(readStatementReview).mockResolvedValue(payload);
    vi.mocked(readReviewHistory).mockResolvedValue([]);
    vi.mocked(decideStatement).mockResolvedValue({ ...payload, review_status: "APPROVED",
      finalization_eligible: true });
    render(<StatementReviewPage token="example-token" statementId={statementId} />);

    expect(await screen.findByText("Built REST API tests in Python.")).toBeInTheDocument();
    expect(screen.getByText("UNREVIEWED")).toBeInTheDocument();
    expect(screen.getByText(/not authorized for trusted finalization/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Approve verified statement" }));

    await waitFor(() =>
      expect(decideStatement).toHaveBeenCalledWith(
        "example-token", statementId, "APPROVED", "version-one-verified",
      ),
    );
    expect(readStatementReview).toHaveBeenCalledWith("example-token", statementId);
  });

  it("disables trusted approval of INFERRED claims but permits rejection", async () => {
    vi.mocked(readStatementReview).mockResolvedValue({
      ...payload, verification_status: "INFERRED",
    });
    vi.mocked(readReviewHistory).mockResolvedValue([]);
    vi.mocked(decideStatement).mockResolvedValue({
      ...payload, verification_status: "INFERRED", review_status: "REJECTED",
    });
    render(<StatementReviewPage token="example-token" statementId={statementId} />);
    expect(await screen.findByText("INFERRED")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve verified statement" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Reject statement" }));
    await waitFor(() => expect(decideStatement).toHaveBeenCalledWith(
      "example-token", statementId, "REJECTED", "version-one-verified",
    ));
  });

  it("fails closed and offers retry when F08 is unavailable", async () => {
    vi.mocked(readStatementReview)
      .mockRejectedValueOnce(new Error("Claim verification is not available."))
      .mockResolvedValueOnce(payload);
    vi.mocked(readReviewHistory).mockResolvedValue([]);
    render(<StatementReviewPage token="example-token" statementId={statementId} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Claim verification is not available.",
    );
    expect(screen.queryByRole("button", { name: "Approve verified statement" }))
      .not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Refresh review" }));
    expect(await screen.findByText("Built REST API tests in Python.")).toBeInTheDocument();
    expect(readStatementReview).toHaveBeenCalledTimes(2);
  });

  it("displays historical changes without presenting stale reviews as final", async () => {
    vi.mocked(readStatementReview).mockResolvedValue({
      ...payload, review_status: "STALE",
      reviewed_revision: "version-old",
    });
    vi.mocked(readReviewHistory).mockResolvedValue([{
      sequence: 1, decision: "APPROVED",
      verification_revision: "version-old",
      decided_at: "2026-11-06T14:00:00Z",
    }]);
    render(<StatementReviewPage token="example-token" statementId={statementId} />);
    expect(await screen.findByText("STALE")).toBeInTheDocument();
    expect(screen.getByText(/changed. Review the latest verified version/i)).toBeInTheDocument();
    expect(screen.getByText(/not authorized for trusted finalization/i)).toBeInTheDocument();
    expect(screen.getByText(/Revision version-old/i)).toBeInTheDocument();
  });
});

// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VerificationPanel } from "./VerificationPanel";
import { STATUS_LABEL, type VerifiedStatementView } from "./types";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const EVIDENCE = ["11111111-1111-1111-1111-111111111111"];

const VERIFIED: VerifiedStatementView = {
  statement_id: "aaaaaaaa-0000-0000-0000-000000000001",
  text: "Built automated regression suites",
  evidence_ids: EVIDENCE,
  status: "VERIFIED",
  revision: "v1-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  findings: [{ reason: "FULLY_COVERED", detail: "100% of the claim's words appear" }],
  export_eligible: true,
};

const UNSUPPORTED: VerifiedStatementView = {
  statement_id: "aaaaaaaa-0000-0000-0000-000000000002",
  text: "Reduced regression runtime by 85%",
  evidence_ids: EVIDENCE,
  status: "UNSUPPORTED",
  revision: "v1-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  findings: [{ reason: "FIGURE_NOT_IN_EVIDENCE", detail: "85%" }],
  export_eligible: false,
};

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const body = handler(url, init);
    return { ok: true, status: 200, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("claim verification", () => {
  it("lists checked claims with their verdicts", async () => {
    mockFetch(() => [VERIFIED, UNSUPPORTED]);

    render(<VerificationPanel token="t" evidenceIds={EVIDENCE} />);

    expect(await screen.findByText("Backed by your evidence")).toBeInTheDocument();
    expect(screen.getByText("Not supported by your evidence")).toBeInTheDocument();
  });

  it("puts the blocked claims first", async () => {
    mockFetch(() => [VERIFIED, UNSUPPORTED]);

    render(<VerificationPanel token="t" evidenceIds={EVIDENCE} />);

    await screen.findByText("Not supported by your evidence");
    const verdicts = screen
      .getAllByText(/Backed by your evidence|Not supported by your evidence/)
      .map((node) => node.textContent);
    expect(verdicts[0]).toBe("Not supported by your evidence");
  });

  it("always says why, quoting what triggered the verdict", async () => {
    mockFetch(() => [UNSUPPORTED]);

    render(<VerificationPanel token="t" evidenceIds={EVIDENCE} />);

    expect(await screen.findByText("Figure is not in your evidence")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("never presents a verdict as an approval of the statement", async () => {
    /**
     * F08 says what the evidence supports; F09 is where the user approves.
     * The page may say "the evidence you approved" — that is F02 evidence
     * approval — but no verdict label may claim the statement was approved.
     */
    mockFetch(() => [VERIFIED, UNSUPPORTED]);

    const { container } = render(<VerificationPanel token="t" evidenceIds={EVIDENCE} />);

    await screen.findByText("Backed by your evidence");
    for (const label of Object.values(STATUS_LABEL)) {
      expect(label).not.toMatch(/approv/i);
    }
    const rendered = container.textContent ?? "";
    expect(rendered).not.toMatch(/approved for export|ready to export|statement approved/i);
    expect(rendered).toMatch(/cannot be exported/i);
  });

  it("submits a claim without sending a status or revision", async () => {
    const fetchMock = mockFetch((url, init) =>
      init?.method === "POST" ? UNSUPPORTED : [],
    );

    render(<VerificationPanel token="t" evidenceIds={EVIDENCE} />);
    await screen.findByText("No claims checked yet.");

    fireEvent.change(screen.getByLabelText("Add a claim to check"), {
      target: { value: "Reduced regression runtime by 85%" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Check this claim" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [, init] = fetchMock.mock.calls[1] as [string, RequestInit];
    const sent = JSON.parse(String(init.body));
    expect(Object.keys(sent).sort()).toEqual(["evidence_ids", "text"]);
  });

  it("refuses to submit when the user has no approved evidence", async () => {
    mockFetch(() => []);

    render(<VerificationPanel token="t" evidenceIds={[]} />);
    await screen.findByText(/Approve some career evidence first/);

    fireEvent.change(screen.getByLabelText("Add a claim to check"), {
      target: { value: "A claim" },
    });
    expect(screen.getByRole("button", { name: "Check this claim" })).toBeDisabled();
  });

  it("explains a failure and offers a retry", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Verification is unavailable right now." }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(<VerificationPanel token="t" evidenceIds={EVIDENCE} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Verification is unavailable right now.",
    );
    fetchMock.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  });
});

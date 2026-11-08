// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InterviewPrepPage } from "./InterviewPrepPage";
import type { ApprovedStatement, InterviewPrep } from "./types";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const STATEMENTS: ApprovedStatement[] = [
  {
    statement_id: "aaaaaaaa-0000-0000-0000-000000000001",
    text: "Reduced regression runtime by 85%",
    evidence_ids: ["11111111-1111-1111-1111-111111111111"],
    verification_status: "VERIFIED",
  },
];

const PREP: InterviewPrep = {
  prep_id: "ffffffff-0000-0000-0000-000000000001",
  user_id: "00000000-0000-0000-0000-0000000000aa",
  generated_at: "2026-01-01T12:00:00Z",
  advisory_only: true,
  items: [
    {
      statement_id: "aaaaaaaa-0000-0000-0000-000000000002",
      statement_text: "Built automated regression suites",
      evidence_ids: ["11111111-1111-1111-1111-111111111111"],
      risk: "SUPPORTED",
      signals: [],
      questions: [
        {
          question_id: "q-1",
          statement_id: "aaaaaaaa-0000-0000-0000-000000000002",
          kind: "EVIDENCE_PROBE",
          text: "Walk me through what you actually did here.",
        },
      ],
      supporting_points: ["Associate QA Engineer at Model N"],
    },
    {
      statement_id: "aaaaaaaa-0000-0000-0000-000000000001",
      statement_text: "Reduced regression runtime by 85%",
      evidence_ids: ["11111111-1111-1111-1111-111111111111"],
      risk: "HARD_TO_DEFEND",
      signals: [{ code: "UNSOURCED_NUMBER", detail: "85%" }],
      questions: [
        {
          question_id: "q-2",
          statement_id: "aaaaaaaa-0000-0000-0000-000000000001",
          kind: "METRIC_SOURCE",
          text: 'Where does the figure "85%" come from?',
        },
      ],
      supporting_points: [],
    },
  ],
};

function mockFetch(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn(async () => ({
    ok,
    status,
    json: async () => body,
  }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("interview preparation", () => {
  it("asks the backend for preparation and shows the questions", async () => {
    const fetchMock = mockFetch(PREP);

    render(<InterviewPrepPage token="test-token" statements={STATEMENTS} />);

    expect(
      await screen.findByText("Walk me through what you actually did here."),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/interview/preparation",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("puts the hardest statements first, whatever order the API returned", async () => {
    mockFetch(PREP);

    render(<InterviewPrepPage token="test-token" statements={STATEMENTS} />);

    await screen.findByText("Hard to defend as written");
    const risks = screen
      .getAllByText(/Hard to defend as written|Your evidence answers this/)
      .map((node) => node.textContent);
    expect(risks[0]).toBe("Hard to defend as written");
  });

  it("names the figure the evidence does not support", async () => {
    mockFetch(PREP);

    render(<InterviewPrepPage token="test-token" statements={STATEMENTS} />);

    expect(
      await screen.findByText("Figure is not in your evidence"),
    ).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("never presents the advice as an approval or verification", async () => {
    mockFetch(PREP);

    const { container } = render(
      <InterviewPrepPage token="test-token" statements={STATEMENTS} />,
    );

    await screen.findByText("Hard to defend as written");
    const rendered = container.textContent ?? "";
    expect(rendered).not.toMatch(/UNSUPPORTED/);
    expect(rendered).not.toMatch(/\bapproved for export\b/i);
    expect(rendered).toMatch(/does not change whether anything is approved/i);
  });

  it("explains a failure and offers a retry", async () => {
    const fetchMock = mockFetch({ detail: "Approved evidence not found" }, false, 404);

    render(<InterviewPrepPage token="test-token" statements={STATEMENTS} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Approved evidence not found",
    );

    fetchMock.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  });

  it("asks the user to approve statements first when there are none", async () => {
    const fetchMock = mockFetch(PREP);

    render(<InterviewPrepPage token="test-token" statements={[]} />);

    expect(
      await screen.findByText(/Approve some resume statements first/),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

// @vitest-environment jsdom
import {
  cleanup,
  render,
  screen,
  fireEvent,
} from "@testing-library/react";

import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { listResumeVersions } from "../applications/api";
import { downloadResume, previewResume } from "./api";
import { ResumePage } from "./ResumePage";

vi.mock("../applications/api", () => ({
  listResumeVersions: vi.fn().mockResolvedValue([]),
}));

vi.mock("./api", () => ({
  downloadResume: vi.fn(),
  previewResume: vi.fn().mockResolvedValue({
    full_name: "Test Applicant", target_role: "Engineer", company: null,
    template: "standard", sections: [],
  }),
}));

afterEach(() => {
  cleanup();
  vi.mocked(listResumeVersions).mockReset();
  vi.mocked(listResumeVersions).mockResolvedValue([]);
  vi.mocked(downloadResume).mockReset();
  vi.unstubAllGlobals();
});

describe("F10 ResumePage", () => {
  it("switches between standard and compact templates", () => {
    render(
      <ResumePage
        token="synthetic-token"
        applicationId="application-123"
      />,
    );

    expect(
      screen.getByText("Selected template: Standard"),
    ).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Resume template"), {
      target: { value: "compact" },
    });

    expect(
      screen.getByText("Selected template: Compact"),
    ).toBeTruthy();
  });

  it("disables downloads when no saved resume versions exist", async () => {
    render(
      <ResumePage
        token="synthetic-token"
        applicationId="application-123"
      />,
    );

    expect(
      await screen.findByText(
        "No saved resume versions are available for this application.",
      ),
    ).toBeTruthy();

    expect(
      (screen.getByRole("button", {
        name: "Download PDF",
      }) as HTMLButtonElement).disabled,
    ).toBe(true);

    expect(
      (screen.getByRole("button", {
        name: "Download Word",
      }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });
it("downloads the selected resume version using the compact template", async () => {
  vi.mocked(listResumeVersions).mockResolvedValue([
    {
      id: "resume-version-456",
      version_number: 2,
      user_id: "user-123",
      application_id: "application-123",
snapshot: {
  user_id: "user-123",
  application_id: "application-123",
  resume_version_id: "resume-version-456",
  created_at: "2026-11-09T10:00:00Z",
  evidence: [],
  statements: [],
},
      created_at: "2026-11-09T10:00:00Z",
    },
  ]);

  vi.mocked(downloadResume).mockResolvedValue(
    new Blob(["sample PDF"], { type: "application/pdf" }),
  );

  const createObjectURL = vi.fn(() => "blob:sample-resume");
  const revokeObjectURL = vi.fn();

  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL,
    revokeObjectURL,
  });

  // jsdom does not perform actual browser downloads.
  // Prevent its anchor navigation from interfering with the test.
  const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => {});

  try {
    render(
      <ResumePage
        token="synthetic-token"
        applicationId="application-123"
      />,
    );

    const pdfButton = await screen.findByRole("button", {
      name: "Download PDF",
    });

    await vi.waitFor(() => {
      expect((pdfButton as HTMLButtonElement).disabled).toBe(false);
    });

    fireEvent.change(screen.getByLabelText("Resume template"), {
      target: { value: "compact" },
    });

    fireEvent.click(pdfButton);

    await vi.waitFor(() => {
      expect(downloadResume).toHaveBeenCalledWith(
        "synthetic-token",
        "resume-version-456",
        "pdf",
        "compact",
      );
    });

    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
  } finally {
    clickSpy.mockRestore();
  }
});
it("displays an error when the backend rejects an export", async () => {
  vi.mocked(listResumeVersions).mockResolvedValue([
    {
      id: "resume-version-456",
      version_number: 2,
      user_id: "user-123",
      application_id: "application-123",
snapshot: {
  user_id: "user-123",
  application_id: "application-123",
  resume_version_id: "resume-version-456",
  created_at: "2026-11-09T10:00:00Z",
  evidence: [],
  statements: [],
},
      created_at: "2026-11-09T10:00:00Z",
    },
  ]);

  vi.mocked(downloadResume).mockRejectedValue(
    new Error("Resume verification is not currently available."),
  );

  render(
    <ResumePage
      token="synthetic-token"
      applicationId="application-123"
    />,
  );

  const pdfButton = await screen.findByRole("button", {
    name: "Download PDF",
  });

  await vi.waitFor(() => {
    expect((pdfButton as HTMLButtonElement).disabled).toBe(false);
  });

  fireEvent.click(pdfButton);

  expect(
    await screen.findByRole("alert"),
  ).toHaveProperty(
    "textContent",
    "Resume verification is not currently available.",
  );
});
});

const savedVersion = (id: string, version_number: number) => ({
  id, version_number, user_id: "user-123", application_id: "application-123",
  created_at: "2026-11-09T10:00:00Z",
  snapshot: {
    user_id: "user-123", application_id: "application-123", resume_version_id: id,
    created_at: "2026-11-09T10:00:00Z", evidence: [], statements: [],
  },
});
const structuredPreview = {
  full_name: "Actual Applicant", target_role: "Engineer", company: null,
  template: "standard" as const,
  sections: [{ heading: "Experience", entries: [{
    evidence_ids: ["evidence-1"], statement_ids: ["statement-1"],
    title: "Analyst", role: "Analyst", organization: "Recorded Employer",
    start_date: "2020-01-02", end_date: "2024-03-04",
    statements: ["Approved experience."],
  }] }],
};
it("renders actual evidence sections and omits unsupported sections", async () => {
  vi.mocked(listResumeVersions).mockResolvedValue([savedVersion("version-1", 1)]);
  vi.mocked(previewResume).mockResolvedValueOnce(structuredPreview);
  render(<ResumePage token="token" applicationId="application-123" />);
  expect(await screen.findByText("Actual Applicant")).toBeTruthy();
  expect(screen.getByText("Analyst | Recorded Employer")).toBeTruthy();
  expect(screen.getByText("2020-01-02 - 2024-03-04")).toBeTruthy();
  expect(screen.getByText("Approved experience.")).toBeTruthy();
  expect(screen.queryByText("Alex Morgan")).toBeNull();
  expect(screen.queryByText("Education")).toBeNull();
  expect(screen.queryByText("Professional Summary")).toBeNull();
});
it("ignores a late preview response after version selection", async () => {
  vi.mocked(listResumeVersions).mockResolvedValue([
    savedVersion("version-2", 2), savedVersion("version-1", 1),
  ]);
  let finishOld!: (value: typeof structuredPreview) => void;
  vi.mocked(previewResume)
    .mockImplementationOnce(() => new Promise((resolve) => { finishOld = resolve; }))
    .mockResolvedValueOnce({ ...structuredPreview, full_name: "Selected Applicant" });
  render(<ResumePage token="token" applicationId="application-123" />);
  await vi.waitFor(() => expect(previewResume).toHaveBeenCalledWith("token", "version-2"));
  fireEvent.change(screen.getByLabelText("Resume version"), { target: { value: "version-1" } });
  expect(await screen.findByText("Selected Applicant")).toBeTruthy();
  finishOld(structuredPreview);
  await vi.waitFor(() => expect(screen.queryByText("Actual Applicant")).toBeNull());
  expect(screen.getByText("Selected Applicant")).toBeTruthy();
});
it("shows a rejected preview without fictional fallback content", async () => {
  vi.mocked(listResumeVersions).mockResolvedValue([savedVersion("version-1", 1)]);
  vi.mocked(previewResume).mockRejectedValueOnce(new Error("Approval is stale."));
  render(<ResumePage token="token" applicationId="application-123" />);
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Approval is stale.");
  expect(screen.queryByLabelText("Validated resume preview")).toBeNull();
  expect(screen.queryByText("Alex Morgan")).toBeNull();
});

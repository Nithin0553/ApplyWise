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
import { downloadResume } from "./api";
import { ResumePage } from "./ResumePage";

vi.mock("../applications/api", () => ({
  listResumeVersions: vi.fn().mockResolvedValue([]),
}));

vi.mock("./api", () => ({
  downloadResume: vi.fn(),
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

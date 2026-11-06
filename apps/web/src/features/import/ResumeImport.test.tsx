// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResumeImport } from "./ResumeImport";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const RECORD = {
  id: "11111111-1111-1111-1111-111111111111",
  user_id: "22222222-2222-2222-2222-222222222222",
  evidence_type: "work_experience",
  title: "Software Engineer Intern",
  organization: "Coastal Analytics",
  role: null,
  location: null,
  description: "Built a Python dashboard.",
  skill_name: null,
  proficiency: null,
  credential: null,
  url: null,
  start_date: "2025-06-01",
  end_date: "2025-08-01",
  source: "resume_import",
  status: "unconfirmed",
  approved_at: null,
  created_at: "2026-10-05T12:00:00Z",
  updated_at: "2026-10-05T12:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function choose(file: File) {
  fireEvent.change(screen.getByLabelText(/resume file/i), { target: { files: [file] } });
}

describe("ResumeImport", () => {
  it("uploads the file and reports the unconfirmed records", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ filename: "resume.docx", records: [RECORD] }, 201),
    );
    vi.stubGlobal("fetch", fetchMock);
    const onImported = vi.fn();

    render(<ResumeImport token="opaque-token" onImported={onImported} />);
    choose(new File(["x"], "resume.docx"));
    fireEvent.click(screen.getByRole("button", { name: "Import resume" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Imported 1 proposed record. They are unconfirmed",
    );
    expect(onImported).toHaveBeenCalledTimes(1);
    expect(onImported.mock.calls[0][0][0]).toMatchObject({
      title: "Software Engineer Intern",
      status: "unconfirmed",
    });

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/evidence\/import$/);
    expect(init.body).toBeInstanceOf(FormData);
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer opaque-token");
    // The browser must set the multipart boundary itself.
    expect(headers.get("Content-Type")).toBeNull();
  });

  it("asks for a file before calling the API", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<ResumeImport token="t" onImported={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Import resume" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Choose a PDF or Word (.docx) resume");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects unsupported file types without uploading", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<ResumeImport token="t" onImported={vi.fn()} />);
    choose(new File(["x"], "photo.png"));
    fireEvent.click(screen.getByRole("button", { name: "Import resume" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Only PDF (.pdf) and Word (.docx) resumes can be imported.",
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the server message when the file cannot be processed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "This file could not be processed. Check the file." }, 422),
      ),
    );
    const onImported = vi.fn();

    render(<ResumeImport token="t" onImported={onImported} />);
    choose(new File(["x"], "broken.pdf"));
    fireEvent.click(screen.getByRole("button", { name: "Import resume" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("This file could not be processed."),
    );
    expect(onImported).not.toHaveBeenCalled();
  });
});

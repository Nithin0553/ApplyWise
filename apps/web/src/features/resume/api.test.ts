import { afterEach, describe, expect, it, vi } from "vitest";

import { downloadResume, ResumeExportError } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("F10 resume download API", () => {
  it("requests a trusted PDF with authentication and template selection", async () => {
    const pdf = new Blob(["synthetic-pdf"], {
      type: "application/pdf",
    });

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => pdf,
    });

    vi.stubGlobal("fetch", fetchMock);

    const result = await downloadResume(
      "synthetic-token",
      "version-123",
      "pdf",
      "compact",
    );

    expect(result).toBe(pdf);
    expect(fetchMock).toHaveBeenCalledOnce();

    const [url, options] = fetchMock.mock.calls[0];

    expect(url).toContain(
      "/api/documents/resume-versions/version-123/export",
    );
    expect(url).toContain("format=pdf");
    expect(url).toContain("template=compact");
    expect(options.method).toBe("GET");
    expect(options.headers.Authorization).toBe("Bearer synthetic-token");
  });

  it("requests a DOCX using the standard template", async () => {
    const document = new Blob(["synthetic-docx"]);

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        blob: async () => document,
      }),
    );

    const result = await downloadResume(
      "synthetic-token",
      "version-456",
      "docx",
      "standard",
    );

    expect(result).toBe(document);
  });

  it("rejects downloads when verification is outdated", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
      }),
    );

    await expect(
      downloadResume(
        "synthetic-token",
        "version-123",
        "pdf",
        "standard",
      ),
    ).rejects.toThrow(
      "This resume requires updated verification or approval",
    );
  });

  it("reports unavailable verification services", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
      }),
    );

    await expect(
      downloadResume(
        "synthetic-token",
        "version-123",
        "pdf",
        "standard",
      ),
    ).rejects.toMatchObject({
      name: "ResumeExportError",
      status: 503,
    } satisfies Partial<ResumeExportError>);
  });

  it("does not download a resume belonging to another user", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
      }),
    );

    await expect(
      downloadResume(
        "synthetic-token",
        "foreign-version",
        "pdf",
        "standard",
      ),
    ).rejects.toMatchObject({
      status: 404,
    });
  });
});

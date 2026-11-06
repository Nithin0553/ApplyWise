import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildReviewerShareUrl,
  createShare,
  listOwnedShares,
  listShareableResumeVersions,
  readReviewerShareSecret,
  resolveShare,
  submitPeerFeedback,
} from "./api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("sharing API", () => {
  it("uses the F01 bearer token when listing owned shares", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await listOwnedShares("synthetic-token");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/shares/");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer synthetic-token");
  });

  it("creates a version-specific share with the requested expiration", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        grant: {
          id: "share-1",
          owner_user_id: "owner-1",
          resume_version_id: "version-1",
          expires_at: "2026-10-20T12:00:00Z",
          revoked_at: null,
          created_at: "2026-10-06T12:00:00Z",
        },
        secret: "synthetic-share-secret-123456",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createShare("token", "version-1", "2026-10-20T12:00:00Z");

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/shares/resume-versions/version-1");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      expires_at: "2026-10-20T12:00:00Z",
    });
  });

  it("discovers shareable resume versions through the public F13 API", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith("/api/applications/")) {
        return jsonResponse([
          { id: "app-1", company_name: "Synthetic Labs", role_title: "Engineer" },
        ]);
      }
      if (url.endsWith("/api/applications/app-1/resume-versions")) {
        return jsonResponse([
          {
            id: "version-1",
            application_id: "app-1",
            version_number: 2,
            created_at: "2026-10-05T12:00:00Z",
          },
        ]);
      }
      return jsonResponse({ detail: "Unexpected request" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const versions = await listShareableResumeVersions("token");

    expect(versions).toEqual([
      {
        id: "version-1",
        applicationId: "app-1",
        versionNumber: 2,
        createdAt: "2026-10-05T12:00:00Z",
        label: "Synthetic Labs — Engineer — Resume v2",
      },
    ]);
  });

  it("keeps the reviewer secret in request bodies and never in API URLs", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          share_id: "share-1",
          resume_version_id: "version-1",
          created_at: "2026-10-06T12:00:00Z",
          expires_at: null,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          id: "feedback-1",
          share_id: "share-1",
          resume_version_id: "version-1",
          reviewer_user_id: "reviewer-1",
          comment: "Keep the strongest outcome first.",
          created_at: "2026-10-06T13:00:00Z",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const secret = "synthetic-share-secret-123456";
    await resolveShare("reviewer-token", secret);
    await submitPeerFeedback("reviewer-token", secret, "  Keep the strongest outcome first.  ");

    const [resolveUrl, resolveInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(resolveUrl).toBe("/api/shares/reviewer/resolve");
    expect(resolveUrl).not.toContain(secret);
    expect(resolveInit.method).toBe("POST");
    expect(JSON.parse(String(resolveInit.body))).toEqual({ secret });

    const [feedbackUrl, feedbackInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(feedbackUrl).toBe("/api/shares/reviewer/feedback");
    expect(feedbackUrl).not.toContain(secret);
    expect(feedbackInit.method).toBe("POST");
    expect(JSON.parse(String(feedbackInit.body))).toEqual({
      secret,
      comment: "Keep the strongest outcome first.",
    });
    expect(String(feedbackInit.body)).not.toContain("reviewer_user_id");
  });

  it("keeps the one-time reviewer secret in the client-only URL fragment", () => {
    const url = buildReviewerShareUrl(
      "synthetic-share-secret-123456",
      "https://applywise.example",
    );

    expect(url).toBe("https://applywise.example/#share=synthetic-share-secret-123456");
    expect(readReviewerShareSecret("#share=synthetic-share-secret-123456")).toBe(
      "synthetic-share-secret-123456",
    );
  });
});

import type {
  PeerFeedbackSummary,
  ShareableResumeVersion,
  ShareGrantSummary,
  SharedResumeReference,
} from "./types";

// Empty means same-origin. Local development can still override this through
// VITE_API_BASE_URL, while production builds never silently point at localhost.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class SharingApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "SharingApiError";
    this.status = status;
  }
}

export interface ShareGrantApiRecord {
  id: string;
  owner_user_id: string;
  resume_version_id: string;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface ShareCreatedApiRecord {
  grant: ShareGrantApiRecord;
  secret: string;
}

export interface PeerFeedbackApiRecord {
  id: string;
  share_id: string;
  resume_version_id: string;
  reviewer_user_id: string;
  comment: string;
  created_at: string;
}

export interface SharedResumeAccessApiRecord {
  share_id: string;
  resume_version_id: string;
  created_at: string;
  expires_at: string | null;
}

interface ApplicationDiscoveryRecord {
  id: string;
  company_name: string;
  role_title: string;
}

interface ResumeVersionDiscoveryRecord {
  id: string;
  application_id: string;
  version_number: number;
  created_at: string;
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        const messages = detail
          .map((item) =>
            item && typeof item === "object" && "msg" in item ? String(item.msg) : null,
          )
          .filter((message): message is string => Boolean(message));
        if (messages.length > 0) return messages.join(" ");
      }
    }
  } catch {
    // Fall through to the generic HTTP message.
  }
  return `Request failed with status ${response.status}.`;
}

async function requestJson<T>(
  token: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new SharingApiError(await extractErrorMessage(response), response.status);
  }
  return (await response.json()) as T;
}

export function listOwnedShares(token: string): Promise<ShareGrantApiRecord[]> {
  return requestJson<ShareGrantApiRecord[]>(token, "/api/shares/");
}

export function createShare(
  token: string,
  resumeVersionId: string,
  expiresAt: string | null,
): Promise<ShareCreatedApiRecord> {
  return requestJson<ShareCreatedApiRecord>(
    token,
    `/api/shares/resume-versions/${encodeURIComponent(resumeVersionId)}`,
    {
      method: "POST",
      body: JSON.stringify({ expires_at: expiresAt }),
    },
  );
}

export function revokeShare(
  token: string,
  shareId: string,
): Promise<ShareGrantApiRecord> {
  return requestJson<ShareGrantApiRecord>(
    token,
    `/api/shares/${encodeURIComponent(shareId)}/revoke`,
    { method: "POST" },
  );
}

export function listPeerFeedback(
  token: string,
  shareId: string,
): Promise<PeerFeedbackApiRecord[]> {
  return requestJson<PeerFeedbackApiRecord[]>(
    token,
    `/api/shares/${encodeURIComponent(shareId)}/feedback`,
  );
}

export function resolveShare(
  token: string,
  secret: string,
): Promise<SharedResumeAccessApiRecord> {
  return requestJson<SharedResumeAccessApiRecord>(token, "/api/shares/reviewer/resolve", {
    method: "POST",
    body: JSON.stringify({ secret }),
  });
}

export function submitPeerFeedback(
  token: string,
  secret: string,
  comment: string,
): Promise<PeerFeedbackApiRecord> {
  return requestJson<PeerFeedbackApiRecord>(token, "/api/shares/reviewer/feedback", {
    method: "POST",
    body: JSON.stringify({ secret, comment: comment.trim() }),
  });
}

/**
 * Discover immutable F13 resume versions that can be targeted by F14.
 * This uses the public F13 HTTP contract rather than reaching into another
 * module's storage or inventing a second version model.
 */
export async function listShareableResumeVersions(
  token: string,
): Promise<ShareableResumeVersion[]> {
  const applications = await requestJson<ApplicationDiscoveryRecord[]>(
    token,
    "/api/applications/",
  );

  const versionGroups = await Promise.all(
    applications.map(async (application) => {
      const versions = await requestJson<ResumeVersionDiscoveryRecord[]>(
        token,
        `/api/applications/${encodeURIComponent(application.id)}/resume-versions`,
      );
      return versions.map((version) => ({
        id: version.id,
        applicationId: version.application_id,
        versionNumber: version.version_number,
        createdAt: version.created_at,
        label: `${application.company_name} — ${application.role_title} — Resume v${version.version_number}`,
      }));
    }),
  );

  return versionGroups.flat();
}

export function toShareGrantSummary(
  record: ShareGrantApiRecord,
  resumeVersionLabels: ReadonlyMap<string, string> = new Map(),
): ShareGrantSummary {
  return {
    id: record.id,
    resumeVersionId: record.resume_version_id,
    resumeVersionLabel:
      resumeVersionLabels.get(record.resume_version_id) ??
      `Resume version ${record.resume_version_id.slice(0, 8)}`,
    createdAt: record.created_at,
    expiresAt: record.expires_at,
    revokedAt: record.revoked_at,
  };
}

export function toPeerFeedbackSummary(record: PeerFeedbackApiRecord): PeerFeedbackSummary {
  return {
    id: record.id,
    // Reviewer identity is intentionally not exposed on the owner-facing UI.
    reviewerLabel: "Reviewer",
    comment: record.comment,
    createdAt: record.created_at,
  };
}

export function toSharedResumeReference(
  record: SharedResumeAccessApiRecord,
): SharedResumeReference {
  return {
    shareId: record.share_id,
    resumeVersionId: record.resume_version_id,
    createdAt: record.created_at,
    expiresAt: record.expires_at,
  };
}

/**
 * Put the one-time share secret in the URL fragment rather than the query
 * string. Fragments stay client-side and are not sent in the HTTP request or
 * Referer header.
 */
export function buildReviewerShareUrl(
  secret: string,
  origin: string = window.location.origin,
): string {
  const url = new URL(origin);
  url.hash = new URLSearchParams({ share: secret }).toString();
  return url.toString();
}

/** Read a reviewer secret from the client-only URL fragment. */
export function readReviewerShareSecret(
  hash: string = window.location.hash,
): string | null {
  const normalized = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!normalized) return null;
  return new URLSearchParams(normalized).get("share");
}

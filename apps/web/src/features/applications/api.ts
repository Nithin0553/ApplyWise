import type {
  ApplicationFormValues,
  ApplicationStatus,
  ApplicationSummary,
  ResumeVersionSummary,
} from "./types";

// Same-origin by default so production bundles never silently point at a
// developer machine. Deployments with a separate API origin can opt in via
// VITE_API_BASE_URL.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApplicationsApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApplicationsApiError";
    this.status = status;
  }
}

export interface ApplicationApiRecord {
  id: string;
  user_id: string;
  company_name: string;
  role_title: string;
  location: string | null;
  job_url: string | null;
  source: string | null;
  notes: string | null;
  status: ApplicationStatus;
  applied_on: string | null;
  next_action_on: string | null;
  closed_on: string | null;
  created_at: string;
  updated_at: string;
}

/** Historical snapshot states. These are not an export/finalization decision. */
export type VerificationSnapshotStatus = "VERIFIED" | "INFERRED" | "UNSUPPORTED";
export type ApprovalSnapshotStatus = "UNREVIEWED" | "APPROVED" | "REJECTED";

export interface EvidenceSnapshotItem {
  evidence_id: string;
  evidence_type: string;
  title: string;
  organization: string | null;
  role: string | null;
  description: string | null;
  approved_at: string;
}

export interface ProvenanceSnapshotItem {
  statement_id: string;
  text: string;
  evidence_ids: string[];
  verification_status: VerificationSnapshotStatus;
  approval_status: ApprovalSnapshotStatus;
}

/**
 * Read model for an immutable F13 historical version. It deliberately retains
 * the verification and approval states that existed at save time. F10 owns the
 * separate finalization/export eligibility boundary and must not infer export
 * permission merely from the fact that a historical F13 version exists.
 */
export interface ResumeVersionSnapshot {
  user_id: string;
  application_id: string;
  resume_version_id: string;
  created_at: string;
  evidence: EvidenceSnapshotItem[];
  statements: ProvenanceSnapshotItem[];
}

export interface ResumeVersionApiRecord {
  id: string;
  user_id: string;
  application_id: string;
  version_number: number;
  snapshot: ResumeVersionSnapshot;
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
    // Fall through to the generic HTTP error below.
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
    throw new ApplicationsApiError(await extractErrorMessage(response), response.status);
  }
  return (await response.json()) as T;
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function applicationPayload(values: ApplicationFormValues) {
  return {
    company_name: values.companyName.trim(),
    role_title: values.roleTitle.trim(),
    location: optionalText(values.location),
    job_url: optionalText(values.jobUrl),
    source: optionalText(values.source),
    notes: optionalText(values.notes),
    applied_on: optionalText(values.appliedOn),
    next_action_on: optionalText(values.nextActionOn),
  };
}

export function listApplications(
  token: string,
  status?: ApplicationStatus,
): Promise<ApplicationApiRecord[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return requestJson<ApplicationApiRecord[]>(token, `/api/applications/${query}`);
}

export function createApplication(
  token: string,
  values: ApplicationFormValues,
): Promise<ApplicationApiRecord> {
  return requestJson<ApplicationApiRecord>(token, "/api/applications/", {
    method: "POST",
    body: JSON.stringify(applicationPayload(values)),
  });
}

export function updateApplication(
  token: string,
  applicationId: string,
  values: ApplicationFormValues,
): Promise<ApplicationApiRecord> {
  return requestJson<ApplicationApiRecord>(
    token,
    `/api/applications/${encodeURIComponent(applicationId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(applicationPayload(values)),
    },
  );
}

export function transitionApplicationStatus(
  token: string,
  applicationId: string,
  status: ApplicationStatus,
  occurredOn?: string,
): Promise<ApplicationApiRecord> {
  return requestJson<ApplicationApiRecord>(
    token,
    `/api/applications/${encodeURIComponent(applicationId)}/status`,
    {
      method: "POST",
      body: JSON.stringify({
        status,
        ...(occurredOn ? { occurred_on: occurredOn } : {}),
      }),
    },
  );
}

export function listResumeVersions(
  token: string,
  applicationId: string,
): Promise<ResumeVersionApiRecord[]> {
  return requestJson<ResumeVersionApiRecord[]>(
    token,
    `/api/applications/${encodeURIComponent(applicationId)}/resume-versions`,
  );
}

export function getResumeVersion(
  token: string,
  resumeVersionId: string,
): Promise<ResumeVersionApiRecord> {
  return requestJson<ResumeVersionApiRecord>(
    token,
    `/api/applications/resume-versions/${encodeURIComponent(resumeVersionId)}`,
  );
}

export function toApplicationSummary(
  record: ApplicationApiRecord,
  versionCount: number,
): ApplicationSummary {
  return {
    id: record.id,
    companyName: record.company_name,
    roleTitle: record.role_title,
    status: record.status,
    location: record.location,
    appliedOn: record.applied_on,
    nextActionOn: record.next_action_on,
    versionCount,
  };
}

export function toApplicationFormValues(
  record: ApplicationApiRecord,
): ApplicationFormValues {
  return {
    companyName: record.company_name,
    roleTitle: record.role_title,
    location: record.location ?? "",
    jobUrl: record.job_url ?? "",
    source: record.source ?? "",
    notes: record.notes ?? "",
    appliedOn: record.applied_on ?? "",
    nextActionOn: record.next_action_on ?? "",
  };
}

export function toResumeVersionSummary(
  record: ResumeVersionApiRecord,
): ResumeVersionSummary {
  return {
    id: record.id,
    versionNumber: record.version_number,
    createdAt: record.created_at,
    statementCount: record.snapshot.statements.length,
  };
}

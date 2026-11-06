import type { CandidateStatement, GenerationResult } from "../tailoring/types";

export interface JourneyEvidence {
  id: string;
  evidence_type: string;
  title: string;
  description: string | null;
  organization: string | null;
  role: string | null;
  status: "approved" | "unconfirmed";
  approved_at: string | null;
}
export interface JourneyApplication {
  id: string;
  company_name: string;
  role_title: string;
  status: string;
  created_at: string;
  notes?: string | null;
  job_url?: string | null;
  applied_on?: string | null;
  next_action_on?: string | null;
  closed_on?: string | null;
}
export interface JourneyResumeVersion {
  id: string;
  version_number: number;
  created_at: string;
  snapshot: {
    statements: Array<{
      statement_id: string;
      text: string;
      evidence_ids: string[];
      verification_status: "VERIFIED" | "INFERRED" | "UNSUPPORTED";
      approval_status: "UNREVIEWED" | "APPROVED" | "REJECTED";
      origin?: "DRAFT_USER_REVIEWED" | "F09_APPROVED";
    }>;
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((item: { msg?: string }) => item.msg ?? "Invalid input").join(", ");
    }
  } catch { /* HTTP error without JSON body */ }
  return `Request failed (HTTP ${response.status}).`;
}

async function api<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as T;
}

export function getEvidence(token: string) {
  return api<JourneyEvidence[]>(token, "/api/evidence/");
}

export function addEvidence(token: string, title: string, role: string, description: string) {
  return api<JourneyEvidence>(token, "/api/evidence/", {
    method: "POST",
    body: JSON.stringify({
      evidence_type: "work_experience", title, role,
      description, source: "User-provided onboarding answer",
    }),
  });
}

export function approveEvidenceItem(token: string, id: string) {
  return api<JourneyEvidence>(token, `/api/evidence/${encodeURIComponent(id)}/approve`, { method: "POST" });
}

export function generateCandidates(
  token: string,
  details: { role: string; company: string; description: string; requirements: string[] },
  approvedIds: string[],
): Promise<GenerationResult> {
  return api<GenerationResult>(token, "/api/generation/preview?provider=demo", {
    method: "POST",
    body: JSON.stringify({
      job_context: {
        job_title: details.role, company: details.company || null,
        description: details.description, requirements: details.requirements,
      },
      evidence_ids: approvedIds.slice(0, 20), max_statements: 10,
    }),
  });
}

export function getApplications(token: string) {
  return api<JourneyApplication[]>(token, "/api/applications/");
}

export const APPLICATION_STATUSES = ["draft", "applied", "interviewing", "offer", "accepted", "rejected", "withdrawn"] as const;
export type JourneyApplicationStatus = typeof APPLICATION_STATUSES[number];

export const ALLOWED_STATUS_CHANGES: Record<JourneyApplicationStatus, readonly JourneyApplicationStatus[]> = {
  draft: ["applied", "interviewing", "offer", "accepted", "rejected", "withdrawn"],
  applied: ["interviewing", "offer", "accepted", "rejected", "withdrawn"],
  interviewing: ["offer", "accepted", "rejected", "withdrawn"],
  offer: ["accepted", "rejected", "withdrawn"],
  accepted: [], rejected: [], withdrawn: [],
};

export function updateApplicationDetails(token: string, id: string, patch: {
  notes?: string | null;
  job_url?: string | null;
  next_action_on?: string | null;
}) {
  return api<JourneyApplication>(token, `/api/applications/${encodeURIComponent(id)}`, {
    method: "PATCH", body: JSON.stringify(patch),
  });
}

export function changeApplicationStatus(token: string, id: string, status: JourneyApplicationStatus) {
  return api<JourneyApplication>(token, `/api/applications/${encodeURIComponent(id)}/status`, {
    method: "POST", body: JSON.stringify({ status }),
  });
}

export function getVersionCounts(token: string) {
  return api<Record<string, number>>(token, "/api/applications/resume-version-counts");
}

export function getVersions(token: string, applicationId: string) {
  return api<JourneyResumeVersion[]>(token, `/api/applications/${encodeURIComponent(applicationId)}/resume-versions`);
}

/**
 * F13 stores provenance snapshots, not an F10 export-eligibility decision.
 * Preserve the honest INFERRED status: a human decision doesn't magically
 * turn a candidate into an F08-verified claim.
 */
export async function saveReviewedResume(
  token: string,
  details: { role: string; company: string; description: string },
  evidence: JourneyEvidence[],
  approved: CandidateStatement[],
) {
  if (!approved.length) throw new Error("No approved statements to save.");
  const ids = new Set(
    evidence.filter(item => item.status === "approved" && item.approved_at)
      .map(item => item.id),
  );
  if (approved.some(statement => !statement.evidence_ids.length ||
    statement.evidence_ids.some(id => !ids.has(id)))) {
    throw new Error("A statement references evidence that is no longer approved.");
  }

  // Send the user's explicit review decisions, not self-asserted evidence
  // snapshots or VERIFIED labels. The server resolves F02 records and
  // atomically saves an INFERRED historical draft with its application.
  const result = await api<{
    application: JourneyApplication;
    resume_version: JourneyResumeVersion;
  }>(token, "/api/applications/reviewed-drafts", {
    method: "POST",
    body: JSON.stringify({
      application: {
        company_name: details.company.trim() || "Company not specified",
        role_title: details.role.trim() || "Target position",
        notes: `Draft created from a user-supplied job description. ${details.description.slice(0, 240)}`,
      },
      statements: approved.map(statement => ({
        statement_id: statement.statement_id,
        text: statement.text,
        evidence_ids: statement.evidence_ids,
      })),
    }),
  });
  return result.application;
}

/** Rule-based excerpting, not the unmounted F04 backend prototype. */
export function readRequirements(description: string): string[] {
  const lines = description.split(/\r?\n/).map((line) => line.trim())
    .filter((line) => line.length > 8);
  const bullets = lines.filter((line) => /^[-•*]\s+/.test(line))
    .map((line) => line.replace(/^[-•*]\s+/, "").trim());
  if (bullets.length) return bullets.slice(0, 14);
  return lines.filter((line) => !/^(about us|overview|benefits|company|job description|responsibilities|requirements):?$/i.test(line))
    .flatMap((line) => line.split(/(?<=[.!?])\s+/))
    .filter((line) => line.length > 16)
    .slice(0, 10);
}

const COMMON = new Set([
  "with", "your", "this", "that", "will", "have", "from", "they", "them",
  "work", "years", "experience", "skills", "ability", "team", "must",
  "required", "preferred", "knowledge", "strong", "good", "more", "than",
  "role", "position", "using", "build", "able", "working", "looking",
  "develop", "responsible", "including", "across", "company",
]);
function tokens(text: string): string[] {
  return [...new Set((text.toLowerCase().match(/[a-z][a-z+#.]{3,}/g) ?? [])
    .filter((word) => !COMMON.has(word)))];
}
/** Heuristic text overlap only; never call this a verified match or ATS score. */
export function estimateOverlap(requirements: string[], approved: JourneyEvidence[]) {
  const text = approved.map((item) => [item.title, item.description, item.role].join(" ")).join(" ").toLowerCase();
  const words = new Set(tokens(text));
  const matched = requirements.map((requirement) => {
    const terms = tokens(requirement);
    return { text: requirement, matches: terms.filter((word) => words.has(word)) };
  });
  return {
    percentage: matched.length ? Math.round(100 * matched.filter((item) => item.matches.length).length / matched.length) : 0,
    matched,
  };
}

export function downloadReviewedText(
  fullName: string,
  details: { role: string; company: string },
  statements: CandidateStatement[],
) {
  const safeName = (fullName.trim() || "resume").replace(/[^a-z0-9_-]+/gi, "-");
  const body = [
    fullName.trim(), `Target role: ${details.role}`,
    details.company ? `Company: ${details.company}` : "",
    "", "RELEVANT EXPERIENCE", ...statements.map((item) => `• ${item.text}`),
    "", "User-reviewed draft. Automated claim verification is not yet available.",
  ].filter((line) => line !== undefined).join("\n");
  const url = URL.createObjectURL(new Blob([body], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${safeName}-reviewed-resume.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 500);
}

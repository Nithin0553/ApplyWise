export type ApplicationStatus =
  | "draft"
  | "applied"
  | "interviewing"
  | "offer"
  | "accepted"
  | "rejected"
  | "withdrawn";

export interface ApplicationSummary {
  id: string;
  companyName: string;
  roleTitle: string;
  status: ApplicationStatus;
  location?: string | null;
  appliedOn?: string | null;
  nextActionOn?: string | null;
  versionCount: number;
}

export interface ResumeVersionSummary {
  id: string;
  versionNumber: number;
  createdAt: string;
  statementCount: number;
}

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  draft: "Draft",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const ALLOWED_APPLICATION_TRANSITIONS: Record<
  ApplicationStatus,
  readonly ApplicationStatus[]
> = {
  draft: ["applied", "interviewing", "offer", "accepted", "rejected", "withdrawn"],
  applied: ["interviewing", "offer", "accepted", "rejected", "withdrawn"],
  interviewing: ["offer", "accepted", "rejected", "withdrawn"],
  offer: ["accepted", "rejected", "withdrawn"],
  accepted: [],
  rejected: [],
  withdrawn: [],
};

export function allowedApplicationStatuses(
  currentStatus: ApplicationStatus,
): readonly ApplicationStatus[] {
  return ALLOWED_APPLICATION_TRANSITIONS[currentStatus];
}

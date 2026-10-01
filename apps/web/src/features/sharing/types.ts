export type ShareGrantStatus = "active" | "expired" | "revoked";

export interface ShareGrantSummary {
  id: string;
  resumeVersionId: string;
  resumeVersionLabel: string;
  createdAt: string;
  expiresAt?: string | null;
  revokedAt?: string | null;
}

export interface PeerFeedbackSummary {
  id: string;
  reviewerLabel: string;
  comment: string;
  createdAt: string;
}

export function getShareGrantStatus(
  share: ShareGrantSummary,
  now: Date = new Date(),
): ShareGrantStatus {
  if (share.revokedAt) {
    return "revoked";
  }

  if (share.expiresAt) {
    const expiresAt = new Date(share.expiresAt);
    if (!Number.isNaN(expiresAt.getTime()) && expiresAt.getTime() <= now.getTime()) {
      return "expired";
    }
  }

  return "active";
}

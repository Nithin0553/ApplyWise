/**
 * F08 claim verification types, mirroring
 * app/modules/verification/contracts.py and schemas.py.
 *
 * Note what the submission type does NOT carry: status or revision. A client
 * sends a claim and the evidence it cites; F08 decides what the claim is worth.
 */

export type VerificationStatus = "VERIFIED" | "INFERRED" | "UNSUPPORTED";

export type VerificationReason =
  | "FIGURE_NOT_IN_EVIDENCE"
  | "ENTITY_NOT_IN_EVIDENCE"
  | "DATE_OUTSIDE_EVIDENCE"
  | "RANKING_NOT_IN_EVIDENCE"
  | "SCOPE_NOT_IN_EVIDENCE"
  | "EVIDENCE_NOT_AVAILABLE"
  | "BEYOND_EVIDENCE_WORDING"
  | "FULLY_COVERED";

export interface VerificationFinding {
  reason: VerificationReason;
  detail: string;
}

export interface VerifiedStatementView {
  statement_id: string;
  text: string;
  evidence_ids: string[];
  status: VerificationStatus;
  revision: string;
  findings: VerificationFinding[];
  export_eligible: boolean;
}

export interface StatementSubmission {
  text: string;
  evidence_ids: string[];
}

/** Plain-language labels. The user should never see a raw enum. */
export const STATUS_LABEL: Record<VerificationStatus, string> = {
  VERIFIED: "Backed by your evidence",
  INFERRED: "Your wording, grounded in evidence",
  UNSUPPORTED: "Not supported by your evidence",
};

export const STATUS_HELP: Record<VerificationStatus, string> = {
  VERIFIED: "The evidence you cited contains what this claim says.",
  INFERRED:
    "Nothing here is invented, but the wording goes beyond what your evidence literally records. You can still approve it.",
  UNSUPPORTED:
    "This claim states something your evidence does not contain, so it cannot be exported.",
};

export const REASON_LABEL: Record<VerificationReason, string> = {
  FIGURE_NOT_IN_EVIDENCE: "Figure is not in your evidence",
  ENTITY_NOT_IN_EVIDENCE: "Names something your evidence does not mention",
  DATE_OUTSIDE_EVIDENCE: "Date falls outside what your evidence records",
  RANKING_NOT_IN_EVIDENCE: "Claims a ranking your evidence does not record",
  SCOPE_NOT_IN_EVIDENCE: "Claims scope your evidence does not record",
  EVIDENCE_NOT_AVAILABLE: "Cited evidence is no longer approved",
  BEYOND_EVIDENCE_WORDING: "Wording goes beyond the evidence",
  FULLY_COVERED: "Every part of this claim appears in your evidence",
};

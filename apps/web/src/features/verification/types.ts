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
  VERIFIED: "Matches your experience",
  INFERRED: "Reworded from your experience",
  UNSUPPORTED: "Not in your experience",
};

export const STATUS_HELP: Record<VerificationStatus, string> = {
  VERIFIED: "Everything this line says appears in the experience it was written from.",
  INFERRED:
    "Nothing here is made up, but the wording goes further than what you wrote down. You can still use it.",
  UNSUPPORTED:
    "This line says something your experience does not contain, so it cannot go on your resume.",
};

export const REASON_LABEL: Record<VerificationReason, string> = {
  FIGURE_NOT_IN_EVIDENCE: "This number is not in your experience",
  ENTITY_NOT_IN_EVIDENCE: "Mentions something you have not written down",
  DATE_OUTSIDE_EVIDENCE: "The dates do not match what you wrote down",
  RANKING_NOT_IN_EVIDENCE: "Says you were ranked highest, which you have not written down",
  SCOPE_NOT_IN_EVIDENCE: "Claims more than you wrote down",
  EVIDENCE_NOT_AVAILABLE: "The experience this used is no longer confirmed",
  BEYOND_EVIDENCE_WORDING: "The wording goes further than what you wrote down",
  FULLY_COVERED: "Everything here appears in your experience",
};

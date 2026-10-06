// Mirrors the F07 contract in apps/api/app/modules/generation/schemas.py.
// Keep these in step with that file; it is the source of truth.

/**
 * One approved evidence item as the picker displays it.
 *
 * This is display data only. It is never sent to generation: the request
 * carries ids, and the server reads the records themselves from F02. So a
 * tampered copy of this object changes what the user sees in the list and
 * nothing about what a statement is grounded in.
 */
export interface EvidenceOption {
  evidence_id: string;
  evidence_type: string;
  title: string;
  organization?: string | null;
  description?: string | null;
}

export interface JobContext {
  job_title: string;
  company?: string | null;
  description: string;
  requirements: string[];
}

export interface GenerationRequest {
  // No user_id: identity comes from the bearer token (F01).
  // No evidence content: only ids. The server resolves them against the
  // caller's own approved evidence (F02), so neither the content nor the
  // approval state can be supplied by the browser.
  job_context: JobContext;
  evidence_ids: string[];
  max_statements: number;
}

export interface CandidateStatement {
  statement_id: string;
  text: string;
  evidence_ids: string[];
  status: "CANDIDATE";
  verification_status: "PENDING";
  approval_status: "UNREVIEWED";
  export_eligible: false;
}

export interface RejectedCandidate {
  text: string;
  reason: string;
}

export interface GenerationResult {
  generation_id: string;
  user_id: string;
  provider: string;
  generated_at: string;
  statements: CandidateStatement[];
  rejected: RejectedCandidate[];
}

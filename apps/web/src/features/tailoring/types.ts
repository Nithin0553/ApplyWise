// Mirrors the F07 contract in apps/api/app/modules/generation/schemas.py.
// Keep these in step with that file; it is the source of truth.

export interface GenerationEvidence {
  evidence_id: string;
  evidence_type: string;
  title: string;
  organization?: string | null;
  role?: string | null;
  location?: string | null;
  description?: string | null;
  // Structured fields from F02's grounding context. Skill and certification
  // evidence often has no description, so these carry the meaning.
  skill_name?: string | null;
  proficiency?: string | null;
  credential?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface JobContext {
  job_title: string;
  company?: string | null;
  description: string;
  requirements: string[];
}

export interface GenerationRequest {
  // No user_id: the server takes identity from the bearer token (F01).
  job_context: JobContext;
  approved_evidence: GenerationEvidence[];
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

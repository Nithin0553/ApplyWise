/**
 * F11 cover letter API layer.
 *
 * Mirrors features/tailoring/api.ts: components never call fetch() directly,
 * and swapping a stub for a real endpoint is one flag plus one function here.
 */

import { ApiError } from "../tailoring/api";
import { USE_REAL, type AiProvider } from "../tailoring/config";
import type { JobContext } from "../tailoring/types";

export interface ApprovedStatement {
  statement_id: string;
  text: string;
  evidence_ids: string[];
  verification_status: "VERIFIED" | "INFERRED";
  approval_status: "APPROVED";
}

export interface CoverLetterParagraph {
  paragraph_id: string;
  text: string;
  statement_ids: string[];
  evidence_ids: string[];
  status: "CANDIDATE";
  verification_status: "PENDING";
  approval_status: "UNREVIEWED";
  export_eligible: false;
}

export interface CoverLetterDraft {
  draft_id: string;
  user_id: string;
  provider: string;
  generated_at: string;
  tone: string;
  paragraphs: CoverLetterParagraph[];
  rejected: { text: string; reason: string }[];
}

export interface CoverLetterRequest {
  // No user_id: the server takes identity from the bearer token (F01).
  job_context: JobContext;
  approved_statements: ApprovedStatement[];
  tone: "professional" | "warm" | "direct";
  max_paragraphs: number;
}

export async function generateCoverLetter(
  request: CoverLetterRequest,
  provider: AiProvider,
  token: string | null,
): Promise<CoverLetterDraft> {
  if (!USE_REAL.f11_coverLetter) {
    throw new ApiError("Cover letter generation is disabled in this build.");
  }

  if (!token) {
    throw new ApiError("You are signed out. Sign in again to draft a letter.");
  }

  let response: Response;
  try {
    response = await fetch(`/api/generation/cover-letter/preview?provider=${provider}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });
  } catch {
    throw new ApiError("Could not reach the API. Is the backend running on port 8000?");
  }

  if (response.status === 401) {
    throw new ApiError("Your session has expired. Sign in again.");
  }
  if (response.status === 403) {
    throw new ApiError("This account does not have permission to draft cover letters.");
  }
  if (response.status === 422) {
    throw new ApiError(
      "Rejected: a cover letter can only be drafted from verified, approved statements.",
    );
  }
  if (response.status === 503) {
    throw new ApiError("The AI provider is unavailable. Nothing was drafted.");
  }
  if (response.status === 502) {
    throw new ApiError("The AI provider returned an unusable response.");
  }
  if (!response.ok) {
    throw new ApiError(`Cover letter generation failed (HTTP ${response.status}).`);
  }

  return (await response.json()) as CoverLetterDraft;
}

/** Stands in for F09's approved statements until verification and approval merge. */
export const SAMPLE_APPROVED_STATEMENTS: ApprovedStatement[] = [
  {
    statement_id: "aaaaaaaa-0000-0000-0000-000000000001",
    text: "Built and maintained automated regression suites for revenue management software",
    evidence_ids: ["11111111-1111-1111-1111-111111111111"],
    verification_status: "VERIFIED",
    approval_status: "APPROVED",
  },
  {
    statement_id: "aaaaaaaa-0000-0000-0000-000000000002",
    text: "Wrote Python test automation for a backend service delivered by a six-person team",
    evidence_ids: ["22222222-2222-2222-2222-222222222222"],
    verification_status: "VERIFIED",
    approval_status: "APPROVED",
  },
  {
    statement_id: "aaaaaaaa-0000-0000-0000-000000000003",
    text: "Owned release-candidate test cycles with engineers and product owners",
    evidence_ids: ["22222222-2222-2222-2222-222222222222"],
    verification_status: "INFERRED",
    approval_status: "APPROVED",
  },
];

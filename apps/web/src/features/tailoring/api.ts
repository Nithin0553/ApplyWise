/**
 * The one place the tailoring UI talks to a backend.
 *
 * Each function checks its feature's flag in config.ts: real call, or stub
 * data. Components never call fetch() directly, so swapping a stub for a
 * teammate's finished endpoint is a one-line change here plus the flag.
 */

import { USE_REAL, type AiProvider } from "./config";
import {
  MOCK_APPROVED_EVIDENCE,
  MOCK_GENERATION_RESULT,
} from "./mockData";
import type { EvidenceOption, GenerationRequest, GenerationResult } from "./types";

export class ApiError extends Error {}

/**
 * One approved evidence record exactly as F02 puts it on the wire.
 *
 * Mirrors `ApprovedEvidence` in apps/api/app/modules/evidence/schemas.py.
 * Note the name of the key: F02 calls its primary key `id`, while F07 calls
 * the reference to it `evidence_id`. They are different names for the same
 * value, so they are translated below rather than cast across — a cast would
 * compile and then silently produce `evidence_id: undefined` at runtime.
 *
 * Every field is optional here because this is untrusted wire data, not a
 * promise. `toEvidenceOption` is what turns it into something the picker can show.
 */
interface ApprovedEvidenceWire {
  id?: string;
  evidence_type?: string;
  title?: string;
  organization?: string | null;
  role?: string | null;
  location?: string | null;
  description?: string | null;
  skill_name?: string | null;
  proficiency?: string | null;
  credential?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

/**
 * Translate one F02 record into the shape the evidence picker displays.
 *
 * Only the id is load-bearing: it is what the generation request sends, and
 * the server reads the record itself. The remaining fields are labels for the
 * list. A record with no id is refused rather than shown, because selecting it
 * could not produce anything grounded.
 */
export function toEvidenceOption(raw: ApprovedEvidenceWire): EvidenceOption {
  if (!raw.id) {
    throw new ApiError(
      "Evidence arrived from the evidence service without an id, so nothing could cite it.",
    );
  }
  if (!raw.evidence_type || !raw.title) {
    throw new ApiError(`Evidence ${raw.id} arrived without a type or a title.`);
  }

  return {
    evidence_id: raw.id,
    evidence_type: raw.evidence_type,
    title: raw.title,
    organization: raw.organization ?? null,
    description: raw.description ?? null,
  };
}

/** F02 — approved evidence for the signed-in user. */
export async function fetchApprovedEvidence(
  token: string | null,
): Promise<EvidenceOption[]> {
  if (!USE_REAL.f02_evidence) {
    return MOCK_APPROVED_EVIDENCE;
  }

  // The real route is behind require_role(JOB_SEEKER), so it needs the token.
  if (!token) {
    throw new ApiError("You are signed out. Sign in again to load your evidence.");
  }

  const response = await fetch("/api/evidence/approved", {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (response.status === 401) {
    throw new ApiError("Your session has expired. Sign in again.");
  }
  if (response.status === 403) {
    throw new ApiError("This account does not have permission to read evidence.");
  }
  if (!response.ok) {
    throw new ApiError(`Could not load evidence (HTTP ${response.status}).`);
  }

  const payload = (await response.json()) as ApprovedEvidenceWire[];
  return payload.map(toEvidenceOption);
}

/** F07 — generate candidate statements from approved evidence. */
export async function generateStatements(
  request: GenerationRequest,
  provider: AiProvider,
  token: string | null,
): Promise<GenerationResult> {
  if (!USE_REAL.f07_generation) {
    return MOCK_GENERATION_RESULT;
  }

  if (!token) {
    throw new ApiError("You are signed out. Sign in again to generate statements.");
  }

  let response: Response;
  try {
    response = await fetch(`/api/generation/preview?provider=${provider}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });
  } catch {
    throw new ApiError(
      "Could not reach the API. Is the backend running on port 8000?",
    );
  }

  if (response.status === 401) {
    throw new ApiError("Your session has expired. Sign in again.");
  }
  if (response.status === 403) {
    throw new ApiError("This account does not have permission to generate statements.");
  }
  if (response.status === 422) {
    throw new ApiError("The request was rejected: check the evidence and job fields.");
  }
  if (response.status === 503) {
    throw new ApiError("The AI provider is unavailable. Nothing was generated.");
  }
  if (response.status === 502) {
    throw new ApiError("The AI provider returned an unusable response.");
  }
  if (!response.ok) {
    throw new ApiError(`Generation failed (HTTP ${response.status}).`);
  }

  return (await response.json()) as GenerationResult;
}

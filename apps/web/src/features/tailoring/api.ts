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
import type { GenerationEvidence, GenerationRequest, GenerationResult } from "./types";

export class ApiError extends Error {}

/** F02 — approved evidence for the signed-in user. */
export async function fetchApprovedEvidence(): Promise<GenerationEvidence[]> {
  if (!USE_REAL.f02_evidence) {
    return MOCK_APPROVED_EVIDENCE;
  }
  // When F02 merges, this is the real call. Nothing else in the UI changes.
  const response = await fetch("/api/evidence/approved");
  if (!response.ok) {
    throw new ApiError(`Could not load evidence (HTTP ${response.status}).`);
  }
  return (await response.json()) as GenerationEvidence[];
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

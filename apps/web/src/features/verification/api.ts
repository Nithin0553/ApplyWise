/**
 * F08 verification API layer.
 *
 * Components never call fetch() directly, matching features/interview and
 * features/cover-letter. Paths are relative so the deployed frontend talks to
 * the API on its own origin.
 */

import type { StatementSubmission, VerifiedStatementView } from "./types";

export class VerificationApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "VerificationApiError";
    this.status = status;
  }
}

function messageFor(status: number, detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (status === 401 || status === 403) return "Please sign in again.";
  if (status === 404) return "That statement is no longer available.";
  return "Verification is unavailable right now.";
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = (await response.json())?.detail;
    } catch {
      detail = null;
    }
    throw new VerificationApiError(response.status, messageFor(response.status, detail));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function listStatements(token: string): Promise<VerifiedStatementView[]> {
  return request<VerifiedStatementView[]>("/api/verification/statements", token);
}

export function submitStatement(
  token: string,
  submission: StatementSubmission,
): Promise<VerifiedStatementView> {
  return request<VerifiedStatementView>("/api/verification/statements", token, {
    method: "POST",
    body: JSON.stringify(submission),
  });
}

export function withdrawStatement(token: string, statementId: string): Promise<void> {
  return request<void>(
    `/api/verification/statements/${encodeURIComponent(statementId)}`,
    token,
    { method: "DELETE" },
  );
}

/**
 * F15 interview defensibility API layer.
 *
 * Components never call fetch() directly, matching features/cover-letter and
 * features/tailoring. Paths are relative so the deployed frontend talks to the
 * API on its own origin.
 */

import type { ApprovedStatement, InterviewPrep } from "./types";

export class InterviewApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "InterviewApiError";
    this.status = status;
  }
}

function messageFor(status: number, detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  // FastAPI reports validation failures as a list, so a request the route
  // rejected on its face used to arrive here as "unavailable right now" --
  // a message that sent the reader looking for an outage instead of the
  // oversized request that actually caused it.
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" && "msg" in item
        ? String((item as { msg: unknown }).msg) : null))
      .filter((value): value is string => Boolean(value));
    if (messages.length) return messages.join("; ");
  }
  if (status === 404) {
    return "Some of the evidence behind these statements is no longer approved.";
  }
  if (status === 401 || status === 403) return "Please sign in again.";
  return "Interview preparation is unavailable right now.";
}

/**
 * Ask the backend to prepare interview questions for approved statements.
 *
 * The statements are sent whole only because F09 has no store yet; the
 * evidence they cite is resolved server-side, so the material each claim is
 * checked against is authoritative.
 */
export async function prepareInterview(
  token: string,
  approvedStatements: ApprovedStatement[],
): Promise<InterviewPrep> {
  const response = await fetch("/api/interview/preparation", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ statement_ids: approvedStatements.map((item) => item.statement_id) }),
  });

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = (await response.json())?.detail;
    } catch {
      detail = null;
    }
    throw new InterviewApiError(response.status, messageFor(response.status, detail));
  }

  return (await response.json()) as InterviewPrep;
}

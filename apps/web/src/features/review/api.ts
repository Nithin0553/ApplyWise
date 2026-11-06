/** F09 HTTP client: pass only statement IDs, decisions and F08 revision tokens. */

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export type VerificationStatus = "VERIFIED" | "INFERRED" | "UNSUPPORTED";
export type ReviewStatus = "UNREVIEWED" | "APPROVED" | "REJECTED" | "STALE";
export type ReviewDecision = "APPROVED" | "REJECTED";

export interface StatementReview {
  statement_id: string;
  text: string;
  evidence_ids: string[];
  verification_status: VerificationStatus;
  verification_revision: string;
  review_status: ReviewStatus;
  finalization_eligible: boolean;
  reviewed_revision: string | null;
}

export interface ReviewEvent {
  sequence: number;
  decision: ReviewDecision;
  verification_revision: string;
  decided_at: string;
}

export class ReviewApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ReviewApiError";
  }
}

async function request<T>(
  token: string, path: string, init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let message = "The review could not be updated.";
    try {
      const payload: unknown = await res.json();
      if (payload && typeof payload === "object" && "detail" in payload) {
        const detail = (payload as { detail?: unknown }).detail;
        if (typeof detail === "string") message = detail;
      }
    } catch { /* preserve safe error */ }
    throw new ReviewApiError(message, res.status);
  }
  return res.json() as Promise<T>;
}

export function readStatementReview(token: string, statementId: string) {
  return request<StatementReview>(
    token, `/api/statement-review/${encodeURIComponent(statementId)}`,
  );
}

export function readReviewHistory(token: string, statementId: string) {
  return request<ReviewEvent[]>(
    token, `/api/statement-review/${encodeURIComponent(statementId)}/history`,
  );
}

export function decideStatement(
  token: string, statementId: string,
  decision: ReviewDecision, expectedRevision: string,
) {
  return request<StatementReview>(
    token, `/api/statement-review/${encodeURIComponent(statementId)}/decision`,
    {
      method: "POST",
      body: JSON.stringify({ decision, expected_revision: expectedRevision }),
    },
  );
}

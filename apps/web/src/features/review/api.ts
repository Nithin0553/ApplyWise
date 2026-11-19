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

/** Turn a server error body into something the reader can act on.
 *
 * FastAPI reports validation failures as a list of objects, so a request the
 * route rejected on its face used to fall through to a flat "could not be
 * updated" -- a message that named no cause and left no way to tell a
 * rejected request apart from a server that was down.
 */
function reviewMessage(status: number, detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" && "msg" in item
        ? String((item as { msg: unknown }).msg) : null))
      .filter((value): value is string => Boolean(value));
    if (messages.length) return messages.join("; ");
  }
  if (status === 401 || status === 403) return "Please sign in again.";
  if (status === 404) {
    return "This statement is no longer available. Reload the page and try again.";
  }
  return `The review could not be updated (error ${status}).`;
}

async function request<T>(
  token: string, path: string, init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail: unknown = null;
    try {
      const payload: unknown = await res.json();
      if (payload && typeof payload === "object" && "detail" in payload) {
        detail = (payload as { detail?: unknown }).detail ?? null;
      }
    } catch { /* a non-JSON body leaves detail null */ }
    throw new ReviewApiError(reviewMessage(res.status, detail), res.status);
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

/** Reuse an approval the user already made for identical content.
 *
 * Sends no decision: the server looks for one of this user's own approvals
 * at the same derived revision. The reply says whether the statement is
 * approved, so a caller must read it rather than assume success.
 */
export function carryForwardReview(
  token: string, statementId: string,
): Promise<StatementReview> {
  return request<StatementReview>(
    token,
    `/api/statement-review/${encodeURIComponent(statementId)}/carry-forward`,
    { method: "POST" },
  );
}

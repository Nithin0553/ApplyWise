import { useEffect, useState } from "react";

import {
  decideStatement, readReviewHistory, readStatementReview,
  type ReviewDecision, type ReviewEvent, type StatementReview,
} from "./api";
import "./review.css";

interface Props {
  token: string;
  statementId: string;
}

/** F09's separate UI. F08 still must be wired before trusted approval works. */
export function StatementReviewPage({ token, statementId }: Props) {
  const [review, setReview] = useState<StatementReview | null>(null);
  const [history, setHistory] = useState<ReviewEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setReview(null);
    setHistory([]);
    setLoading(true);
    setError("");
    void readStatementReview(token, statementId)
      .then(async current => {
        if (!active) return;
        setReview(current);
        const events = await readReviewHistory(token, statementId);
        if (active) setHistory(events);
      })
      .catch(cause => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load review.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token, statementId, reload]);

  async function decide(decision: ReviewDecision) {
    if (busy || !review) return;
    setBusy(true);
    setError("");
    try {
      await decideStatement(token, statementId, decision, review.verification_revision);
      setReload(current => current + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Review could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="aw-review" aria-label="Verified statement review">
    <header>
      <h2>Review a resume statement</h2>
      <p>First verify the claim against your real experience. Your approval is a separate decision.</p>
    </header>
    {loading && <p role="status">Loading verified statement…</p>}
    {error && <div className="aw-review-error" role="alert">
      {error}
      <button type="button" onClick={() => setReload(value => value + 1)}>Refresh review</button>
    </div>}
    {!loading && review && <>
      <blockquote>{review.text}</blockquote>
      <dl className="aw-review-status">
        <div><dt>Independent verification</dt><dd>{review.verification_status}</dd></div>
        <div><dt>Your review</dt><dd>{review.review_status}</dd></div>
        <div><dt>Source evidence</dt><dd>{review.evidence_ids.length} references</dd></div>
      </dl>
      {review.review_status === "STALE" &&
        <p role="status">This claim or its evidence changed. Review the latest verified version again.</p>}
      <div className="aw-review-actions">
        <button type="button" disabled={busy || review.verification_status !== "VERIFIED"}
          onClick={() => void decide("APPROVED")}>
          {busy ? "Saving…" : "Approve verified statement"}
        </button>
        <button type="button" disabled={busy} onClick={() => void decide("REJECTED")}>
          Reject statement
        </button>
        <button type="button" disabled={busy} onClick={() => setReload(value => value + 1)}>
          Refresh
        </button>
      </div>
      <p className="aw-review-disclosure">
        {review.finalization_eligible
          ? "This statement currently meets the F09 review requirement. Final resume export still needs F13/F10 authorization."
          : "This statement is not authorized for trusted finalization or export."}
      </p>
      <section aria-label="Decision history" className="aw-review-history">
        <h3>Decision history</h3>
        {history.length ? <ol>{history.map(item =>
          <li key={item.sequence}>
            <strong>{item.decision}</strong> · Revision {item.verification_revision} ·
            {" "}{new Date(item.decided_at).toLocaleString()}
          </li>)}</ol> : <p>No decisions saved yet.</p>}
      </section>
    </>}
  </section>;
}

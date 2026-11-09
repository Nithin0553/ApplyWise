/**
 * F08 claim verification UI.
 *
 * The screen shows each claim, what F08 decided about it, and — always — why.
 * A verdict without a reason is not actionable: a user told "unsupported" with
 * no explanation can only guess, and guessing here means deleting true claims.
 * So every classification renders its findings, quoting the figure or word
 * that triggered it.
 *
 * UNSUPPORTED is shown as a blocked export, not as an accusation. The user may
 * well be right and simply have evidence that does not say so yet; the fix is
 * usually to add evidence, which is what the empty-state copy points at.
 */

import { useCallback, useEffect, useState } from "react";

import { listStatements, submitStatement, withdrawStatement } from "./api";
import {
  REASON_LABEL,
  STATUS_HELP,
  STATUS_LABEL,
  type VerificationStatus,
  type VerifiedStatementView,
} from "./types";
import "./verification.css";

interface Props {
  token: string;
  /** Approved F02 evidence ids a new claim may cite. */
  evidenceIds?: string[];
  onBack?: () => void;
}

const STATUS_ORDER: Record<VerificationStatus, number> = {
  UNSUPPORTED: 0,
  INFERRED: 1,
  VERIFIED: 2,
};

function StatementCard({
  item,
  onWithdraw,
  busy,
}: {
  item: VerifiedStatementView;
  onWithdraw: (id: string) => void;
  busy: boolean;
}) {
  const tone = item.status.toLowerCase();
  return (
    <article className={`vf-card vf-card--${tone}`}>
      <header className="vf-card__header">
        <p className="vf-card__text">{item.text}</p>
        <span className={`vf-status vf-status--${tone}`}>{STATUS_LABEL[item.status]}</span>
      </header>

      <p className="vf-muted">{STATUS_HELP[item.status]}</p>

      {item.findings.length > 0 && (
        <ul className="vf-findings" aria-label="Why this was classified this way">
          {item.findings.map((finding) => (
            <li key={`${finding.reason}-${finding.detail}`} className="vf-finding">
              <strong>{REASON_LABEL[finding.reason]}</strong>
              <span className="vf-finding__detail">{finding.detail}</span>
            </li>
          ))}
        </ul>
      )}

      <footer className="vf-card__footer">
        <span className="vf-muted vf-revision" title="Changes whenever the claim or its evidence changes">
          revision {item.revision.slice(0, 11)}…
        </span>
        <button
          type="button"
          className="vf-link"
          disabled={busy}
          onClick={() => onWithdraw(item.statement_id)}
        >
          Remove
        </button>
      </footer>
    </article>
  );
}

export function VerificationPanel({ token, evidenceIds = [], onBack }: Props) {
  const [items, setItems] = useState<VerifiedStatementView[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await listStatements(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification is unavailable right now.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function add() {
    if (!draft.trim() || !evidenceIds.length) return;
    setBusy(true);
    setError("");
    try {
      const created = await submitStatement(token, {
        text: draft.trim(),
        evidence_ids: evidenceIds,
      });
      setItems((current) => [...current, created]);
      setDraft("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not verify that claim.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(statementId: string) {
    setBusy(true);
    setError("");
    try {
      await withdrawStatement(token, statementId);
      setItems((current) => current.filter((item) => item.statement_id !== statementId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove that claim.");
    } finally {
      setBusy(false);
    }
  }

  const ordered = [...items].sort(
    (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status],
  );
  const blocked = ordered.filter((item) => !item.export_eligible).length;

  return (
    <main className="vf-page" aria-label="Claim verification">
      <header className="vf-page__header">
        {onBack && (
          <button type="button" className="vf-link" onClick={onBack}>
            ← Back to application
          </button>
        )}
        <h2>Check your claims</h2>
        <p className="vf-muted">
          Each claim is compared with the evidence you approved. Claims that state
          something your evidence does not contain cannot be exported.
        </p>
      </header>

      {error && (
        <div className="vf-error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void load()}>
            Try again
          </button>
        </div>
      )}

      <section className="vf-compose">
        <label htmlFor="vf-draft">Add a claim to check</label>
        <textarea
          id="vf-draft"
          value={draft}
          maxLength={500}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="e.g. Built automated regression suites for billing"
        />
        <button type="button" disabled={busy || !draft.trim() || !evidenceIds.length} onClick={() => void add()}>
          Check this claim
        </button>
        {!evidenceIds.length && (
          <p className="vf-muted">
            Approve some career evidence first — a claim can only be checked against
            evidence you own.
          </p>
        )}
      </section>

      {loading && (
        <p className="vf-muted" role="status">
          Comparing your claims with your evidence…
        </p>
      )}

      {!loading && ordered.length === 0 && (
        <p className="vf-muted">No claims checked yet.</p>
      )}

      {!loading && ordered.length > 0 && (
        <>
          <p className="vf-summary">
            {ordered.length} claim{ordered.length === 1 ? "" : "s"} checked
            {blocked > 0 && (
              <>
                {" · "}
                <strong>{blocked} cannot be exported</strong>
              </>
            )}
          </p>
          <div className="vf-list">
            {ordered.map((item) => (
              <StatementCard
                key={item.statement_id}
                item={item}
                onWithdraw={(id) => void remove(id)}
                busy={busy}
              />
            ))}
          </div>
        </>
      )}
    </main>
  );
}

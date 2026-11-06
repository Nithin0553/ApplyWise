/**
 * F15 interview defensibility UI.
 *
 * The screen is deliberately not a score. It shows, per statement, what an
 * interviewer would ask and what the user can answer with. Risk is secondary
 * framing, never a verdict on the statement itself — F08 owns verification,
 * and nothing here may read as though it does.
 */

import { useCallback, useEffect, useState } from "react";

import { prepareInterview } from "./api";
import {
  RISK_LABEL,
  SIGNAL_LABEL,
  type ApprovedStatement,
  type DefensibilityRisk,
  type InterviewPrep,
  type StatementPreparation,
} from "./types";
import "./interview.css";

interface Props {
  token: string;
  /** Approved statements to rehearse. Supplied by F09 once it exists. */
  statements: ApprovedStatement[];
  onBack?: () => void;
}

const RISK_ORDER: Record<DefensibilityRisk, number> = {
  HARD_TO_DEFEND: 0,
  NEEDS_DETAIL: 1,
  SUPPORTED: 2,
};

function PreparationCard({ item }: { item: StatementPreparation }) {
  return (
    <article className={`iv-card iv-card--${item.risk.toLowerCase()}`}>
      <header className="iv-card__header">
        <p className="iv-card__statement">{item.statement_text}</p>
        <span className={`iv-risk iv-risk--${item.risk.toLowerCase()}`}>
          {RISK_LABEL[item.risk]}
        </span>
      </header>

      {item.signals.length > 0 && (
        <ul className="iv-signals" aria-label="Why this may be challenged">
          {item.signals.map((signal) => (
            <li key={`${signal.code}-${signal.detail}`} className="iv-signal">
              <strong>{SIGNAL_LABEL[signal.code]}</strong>
              <span className="iv-signal__detail">{signal.detail}</span>
            </li>
          ))}
        </ul>
      )}

      <section className="iv-section">
        <h4>Expect to be asked</h4>
        <ol className="iv-questions">
          {item.questions.map((question) => (
            <li key={question.question_id}>{question.text}</li>
          ))}
        </ol>
      </section>

      {item.supporting_points.length > 0 && (
        <section className="iv-section">
          <h4>Answer from your own evidence</h4>
          <ul className="iv-points">
            {item.supporting_points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}

export function InterviewPrepPage({ token, statements, onBack }: Props) {
  const [prep, setPrep] = useState<InterviewPrep | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const run = useCallback(async () => {
    if (!statements.length) return;
    setBusy(true);
    setError("");
    try {
      setPrep(await prepareInterview(token, statements));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Interview preparation is unavailable right now.",
      );
    } finally {
      setBusy(false);
    }
  }, [token, statements]);

  useEffect(() => {
    void run();
  }, [run]);

  const ordered = prep
    ? [...prep.items].sort((a, b) => RISK_ORDER[a.risk] - RISK_ORDER[b.risk])
    : [];
  const flagged = ordered.filter((item) => item.risk === "HARD_TO_DEFEND").length;

  return (
    <main className="iv-page" aria-label="Interview preparation">
      <header className="iv-page__header">
        {onBack && (
          <button type="button" className="iv-link" onClick={onBack}>
            ← Back to application
          </button>
        )}
        <h2>Prepare for the interview</h2>
        <p className="iv-muted">
          Questions an interviewer is likely to ask about the statements you
          approved, and what your own evidence lets you answer with. This is
          preparation advice — it does not change whether anything is approved
          or exportable.
        </p>
      </header>

      {error && (
        <div className="iv-error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void run()}>
            Try again
          </button>
        </div>
      )}

      {busy && (
        <p className="iv-muted" role="status">
          Reading your statements against your evidence…
        </p>
      )}

      {!busy && !error && statements.length === 0 && (
        <p className="iv-muted">
          Approve some resume statements first, then come back to rehearse them.
        </p>
      )}

      {!busy && prep && (
        <>
          <p className="iv-summary">
            {ordered.length} statement{ordered.length === 1 ? "" : "s"} reviewed
            {flagged > 0 && (
              <>
                {" · "}
                <strong>{flagged} hard to defend as written</strong>
              </>
            )}
          </p>
          <div className="iv-list">
            {ordered.map((item) => (
              <PreparationCard key={item.statement_id} item={item} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}

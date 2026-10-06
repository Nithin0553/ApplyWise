import type { PageProps } from "../Shell";
import { REVIEW_STATEMENTS } from "../mock";
import { useApprovals } from "../store";

const PILL: Record<string, string> = {
  VERIFIED: "sf-pill sf-pill-ok",
  INFERRED: "sf-pill sf-pill-warn",
  UNSUPPORTED: "sf-pill sf-pill-stop",
};

export function ReviewPage({ go }: PageProps) {
  const { approvedIds: approved, toggle } = useApprovals();

  return (
    <main className="sf-page sf-reveal">
      <header style={{ marginBottom: 28 }}>
        <p className="sf-eyebrow">F08 · F09 · Verification and approval</p>
        <h2 className="sf-h2" style={{ marginTop: 10 }}>
          Checked by the system, <span className="sf-cursive">approved</span> by you
        </h2>
        <p className="sf-lede">
          Verification compares each statement against the evidence it cites. It is a check, not
          permission — only you can approve a line onto your resume.
        </p>
      </header>

      <div className="sf-side">
        <section className="sf-stack">
          {REVIEW_STATEMENTS.map((statement) => {
            const blocked = statement.state === "UNSUPPORTED";
            return (
              <article
                className="sf-card"
                key={statement.id}
                style={blocked ? { background: "#fdf6f5" } : undefined}
              >
                <div className="sf-check">
                  <input
                    type="checkbox"
                    id={statement.id}
                    checked={approved.includes(statement.id)}
                    disabled={blocked}
                    onChange={() => toggle(statement.id)}
                  />
                  <div>
                    <div style={{ marginBottom: 8 }}>
                      <span className={PILL[statement.state]}>{statement.state}</span>
                      {statement.refs.map((ref) => (
                        <span className="sf-chip" key={ref}>
                          {ref}
                        </span>
                      ))}
                      {blocked && <span className="sf-muted">blocked from export</span>}
                    </div>
                    <label
                      htmlFor={statement.id}
                      style={{ fontSize: 17, lineHeight: 1.6, display: "block" }}
                    >
                      {statement.text}
                    </label>
                    <p className="sf-muted" style={{ margin: "10px 0 0", lineHeight: 1.6 }}>
                      {statement.note}
                    </p>
                    {statement.state === "INFERRED" && (
                      <div className="sf-row" style={{ gap: 8, marginTop: 14 }}>
                        <button type="button" className="sf-btn sf-btn-ghost">
                          Edit and re-verify
                        </button>
                        <button type="button" className="sf-btn sf-btn-ghost">
                          Discard
                        </button>
                      </div>
                    )}
                    {blocked && (
                      <div className="sf-row" style={{ gap: 8, marginTop: 14 }}>
                        <button
                          type="button"
                          className="sf-btn sf-btn-ghost"
                          onClick={() => go("evidence")}
                        >
                          Go to evidence
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </section>

        <aside className="sf-stack">
          <div className="sf-card sf-card-lav">
            <h3 className="sf-h3">What the labels mean</h3>
            <dl style={{ margin: 0, lineHeight: 1.55 }}>
              <dt style={{ fontWeight: 500 }}>Verified</dt>
              <dd className="sf-muted" style={{ margin: "2px 0 10px" }}>
                Every claim appears in the cited evidence.
              </dd>
              <dt style={{ fontWeight: 500 }}>Inferred</dt>
              <dd className="sf-muted" style={{ margin: "2px 0 10px" }}>
                Reasonable, but says more than the evidence does.
              </dd>
              <dt style={{ fontWeight: 500 }}>Unsupported</dt>
              <dd className="sf-muted" style={{ margin: "2px 0 0" }}>
                Not backed by approved evidence. Can never be exported.
              </dd>
            </dl>
          </div>

          <div className="sf-card sf-card-sage">
            <div className="sf-eyebrow">Your approval</div>
            <div className="sf-stat">
              {approved.length}
              <span style={{ fontSize: 15, color: "#78716c", marginLeft: 8 }}>
                of {REVIEW_STATEMENTS.length}
              </span>
            </div>
            <p className="sf-muted" style={{ margin: "6px 0 0" }}>
              Editing an approved statement later sends it back for re-verification.
            </p>
          </div>

          <p className="sf-muted" style={{ margin: 0 }}>
            What you approve here is what the cover letter and the resume may use.
          </p>
          <button type="button" className="sf-btn sf-btn-dark" onClick={() => go("cover")}>
            Draft a cover letter from these →
          </button>
          <button type="button" className="sf-btn sf-btn-ghost" onClick={() => go("resume")}>
            Build the resume →
          </button>
        </aside>
      </div>
    </main>
  );
}

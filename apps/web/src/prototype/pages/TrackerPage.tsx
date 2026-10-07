import type { PageProps } from "../Shell";
import { APPLICATIONS } from "../mock";

const STAGES = ["Saved", "Applied", "Interviewing", "Closed"] as const;

export function TrackerPage({ go }: PageProps) {
  return (
    <main className="sf-page sf-reveal">
      <header className="sf-pagehead">
        <h2 className="sf-h2">Applications</h2>
        <p className="sf-lede">
          Each saved version freezes the evidence, the provenance and the approvals as they were
          that day, so an interview months later holds no surprises.
        </p>
      </header>

      <div className="sf-grid sf-grid-4" style={{ marginBottom: 32 }}>
        {STAGES.map((stage) => {
          const items = APPLICATIONS.filter((application) => application.stage === stage);
          return (
            <section className="sf-card" key={stage}>
              <div className="sf-row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
                <strong style={{ fontWeight: 500 }}>{stage}</strong>
                <span className="sf-muted">{items.length}</span>
              </div>
              <div className="sf-stack" style={{ gap: 10 }}>
                {items.map((application) => (
                  <article
                    key={application.company}
                    className={
                      stage === "Interviewing"
                        ? "sf-card sf-card-tight sf-card-sage"
                        : "sf-card sf-card-tight"
                    }
                    style={{ boxShadow: "none", border: "1px solid #f0efec" }}
                  >
                    <div style={{ fontWeight: 500 }}>{application.role}</div>
                    <div className="sf-muted">{application.company}</div>
                    <div className="sf-muted" style={{ marginTop: 8 }}>
                      {application.version} · {application.when}
                    </div>
                  </article>
                ))}
                {items.length === 0 && <p className="sf-muted">Nothing here yet.</p>}
              </div>
            </section>
          );
        })}
      </div>

      <section className="sf-card">
        <h3 className="sf-h3">Software Engineer in Test · version history</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr className="sf-muted" style={{ textAlign: "left" }}>
              <th style={{ padding: "8px 0", fontWeight: 500 }}>Version</th>
              <th style={{ padding: "8px 0", fontWeight: 500 }}>Saved</th>
              <th style={{ padding: "8px 0", fontWeight: 500 }}>Approved statements</th>
              <th style={{ padding: "8px 0", fontWeight: 500 }}>Evidence snapshot</th>
            </tr>
          </thead>
          <tbody>
            {[
              { version: "v3", saved: "30 Sep 2026", statements: 2, evidence: "3 items · frozen" },
              { version: "v2", saved: "28 Sep 2026", statements: 4, evidence: "5 items · frozen" },
              { version: "v1", saved: "26 Sep 2026", statements: 3, evidence: "5 items · frozen" },
            ].map((row) => (
              <tr key={row.version} style={{ borderTop: "1px solid #f5f5f4" }}>
                <td style={{ padding: "12px 0", fontWeight: 500 }}>{row.version}</td>
                <td style={{ padding: "12px 0" }}>{row.saved}</td>
                <td style={{ padding: "12px 0" }}>{row.statements}</td>
                <td style={{ padding: "12px 0" }}>{row.evidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="sf-row" style={{ justifyContent: "center", marginTop: 32 }}>
        <button type="button" className="sf-btn sf-btn-primary" onClick={() => go("jobs")}>
          Tailor for another job
        </button>
      </div>
    </main>
  );
}

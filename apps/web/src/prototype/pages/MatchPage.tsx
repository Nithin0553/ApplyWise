import type { PageProps } from "../Shell";
import { EVIDENCE, REQUIREMENTS } from "../mock";

const PILL: Record<string, string> = {
  Strong: "sf-pill sf-pill-ok",
  Partial: "sf-pill sf-pill-warn",
  Gap: "sf-pill sf-pill-stop",
};

export function MatchPage({ go }: PageProps) {
  const strong = REQUIREMENTS.filter((item) => item.support === "Strong").length;
  const coverage = Math.round((strong / REQUIREMENTS.length) * 100);

  return (
    <main className="sf-page sf-reveal">
      <header style={{ marginBottom: 28 }}>
        <p className="sf-eyebrow">F05 · F06 · Matching and gaps</p>
        <h2 className="sf-h2" style={{ marginTop: 10 }}>
          Where you are strong, and where you are <span className="sf-cursive">honestly</span> not
        </h2>
        <p className="sf-lede">
          A gap is never filled by inventing content. Add real evidence, or leave the gap and let
          the rest of the resume speak.
        </p>
      </header>

      <div className="sf-side">
        <section className="sf-stack">
          {REQUIREMENTS.map((requirement) => (
            <article className="sf-card" key={requirement.name}>
              <div className="sf-row" style={{ justifyContent: "space-between" }}>
                <div style={{ flex: 1, minWidth: 240 }}>
                  <h3 className="sf-h3">{requirement.name}</h3>
                  <p className="sf-muted" style={{ margin: "4px 0 10px" }}>
                    {requirement.note}
                  </p>
                  {requirement.supportedBy.length > 0 ? (
                    <div>
                      {requirement.supportedBy.map((ref) => (
                        <span className="sf-chip" key={ref}>
                          {ref}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="sf-muted">No approved evidence</span>
                  )}
                </div>
                <span className={PILL[requirement.support]}>{requirement.support}</span>
              </div>
            </article>
          ))}
        </section>

        <aside className="sf-stack">
          <div className="sf-card sf-card-sage">
            <div className="sf-eyebrow">Evidence coverage</div>
            <div className="sf-stat">{coverage}%</div>
            <p className="sf-muted" style={{ margin: "4px 0 0" }}>
              {strong} of {REQUIREMENTS.length} requirements strongly supported
            </p>
          </div>

          <div className="sf-card">
            <h3 className="sf-h3">Evidence going forward</h3>
            <p className="sf-muted" style={{ margin: "0 0 12px" }}>
              Only these items are sent to tailoring.
            </p>
            {EVIDENCE.filter((item) => item.status === "APPROVED").map((item) => (
              <label className="sf-check" key={item.id} style={{ marginBottom: 10 }}>
                <input type="checkbox" defaultChecked />
                <span>
                  <span className="sf-chip">{item.ref}</span>
                  {item.title}
                </span>
              </label>
            ))}
          </div>

          <div className="sf-banner sf-banner-warn">
            Add evidence about REST API testing if you have it — that turns a partial match into a
            strong one.
          </div>

          <button type="button" className="sf-btn sf-btn-dark" onClick={() => go("tailor")}>
            Generate statements →
          </button>
        </aside>
      </div>
    </main>
  );
}

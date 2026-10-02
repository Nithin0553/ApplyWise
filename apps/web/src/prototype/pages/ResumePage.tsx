import type { PageProps } from "../Shell";

export function ResumePage({ go }: PageProps) {
  return (
    <main className="sf-page sf-reveal">
      <header style={{ marginBottom: 28 }}>
        <p className="sf-eyebrow">F10 · F12 · Resume and export</p>
        <h2 className="sf-h2" style={{ marginTop: 10 }}>
          Only the lines you <span className="sf-cursive">approved</span>
        </h2>
        <p className="sf-lede">
          Two statements were held back from this version: one inferred, one unsupported. Nothing
          unapproved can reach the page.
        </p>
      </header>

      <div className="sf-side">
        <section className="sf-card" style={{ padding: 40 }}>
          <div style={{ borderBottom: "2px solid #292524", paddingBottom: 14 }}>
            <div style={{ fontSize: 26, fontWeight: 500, letterSpacing: "-0.02em" }}>
              Niraali Deepak Bandi
            </div>
            <div className="sf-muted" style={{ marginTop: 4 }}>
              Corpus Christi, TX · niraali@example.edu · github.com/niraalibandi
            </div>
          </div>

          <h3 className="sf-eyebrow" style={{ marginTop: 24 }}>
            Experience
          </h3>
          <div className="sf-row" style={{ justifyContent: "space-between" }}>
            <strong style={{ fontWeight: 500 }}>Associate QA Engineer, Model N</strong>
            <span className="sf-muted">Jun 2022 – Dec 2024</span>
          </div>
          <ul style={{ margin: "8px 0 0", paddingLeft: 20, lineHeight: 1.65 }}>
            <li style={{ marginBottom: 6 }}>
              Built and maintained automated regression suites for revenue management software,
              supporting release-candidate test cycles.
            </li>
            <li>
              Wrote Python test automation for a backend service delivered by a six-person team.
            </li>
          </ul>

          <h3 className="sf-eyebrow" style={{ marginTop: 24 }}>
            Education
          </h3>
          <div className="sf-row" style={{ justifyContent: "space-between" }}>
            <strong style={{ fontWeight: 500 }}>
              M.S. Computer Science, Texas A&amp;M University–Corpus Christi
            </strong>
            <span className="sf-muted">Expected Dec 2026</span>
          </div>

          <h3 className="sf-eyebrow" style={{ marginTop: 24 }}>
            Skills
          </h3>
          <p style={{ margin: 0, lineHeight: 1.65 }}>
            Python · test automation · pytest · REST API testing · SQL · Git
          </p>

          <div className="sf-banner sf-banner-ok" style={{ marginTop: 28 }}>
            Every line above is approved and traceable to approved evidence.
          </div>
        </section>

        <aside className="sf-stack">
          <div className="sf-card sf-card-sage">
            <div className="sf-eyebrow">ATS readability</div>
            <div className="sf-stat">86</div>
            <ul className="sf-muted" style={{ paddingLeft: 18, lineHeight: 1.6, margin: "8px 0 0" }}>
              <li>Standard section headings found</li>
              <li>No tables or text boxes</li>
              <li>Consider adding “REST API testing”</li>
            </ul>
          </div>

          <div className="sf-card">
            <h3 className="sf-h3">Template</h3>
            <div className="sf-row" style={{ gap: 8 }}>
              <button type="button" className="sf-btn sf-btn-dark">
                Classic
              </button>
              <button type="button" className="sf-btn sf-btn-ghost">
                Compact
              </button>
              <button type="button" className="sf-btn sf-btn-ghost">
                Academic
              </button>
            </div>
          </div>

          <div className="sf-card">
            <h3 className="sf-h3">Export</h3>
            <div className="sf-stack" style={{ gap: 8 }}>
              <button type="button" className="sf-btn sf-btn-primary">
                Download PDF
              </button>
              <button type="button" className="sf-btn sf-btn-ghost">
                Download Word
              </button>
              <button type="button" className="sf-btn sf-btn-ghost">
                Share for peer review
              </button>
            </div>
            <p className="sf-muted" style={{ marginBottom: 0 }}>
              A reviewer link shows this version and its comments only — never your evidence
              profile.
            </p>
          </div>

          <button type="button" className="sf-btn sf-btn-dark" onClick={() => go("tracker")}>
            Save version and track →
          </button>
        </aside>
      </div>
    </main>
  );
}

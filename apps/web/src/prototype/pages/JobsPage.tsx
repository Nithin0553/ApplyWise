import { useState } from "react";

import type { PageProps } from "../Shell";
import { REQUIREMENTS } from "../mock";

const POSTING = `We are hiring a Software Engineer in Test to own automated testing for a Python backend. You will design and maintain automated regression suites, work with engineers on release readiness, and improve our CI pipelines.

Required: 2+ years in software quality assurance, strong test automation experience, and familiarity with REST API testing.

Preferred: experience with performance testing, and exposure to Kubernetes in production.`;

export function JobsPage({ go }: PageProps) {
  const [text, setText] = useState(POSTING);
  const [analysed, setAnalysed] = useState(true);

  return (
    <main className="sf-page sf-reveal">
      <header style={{ marginBottom: 28 }}>
        <p className="sf-eyebrow">F04 · Job description analysis</p>
        <h2 className="sf-h2" style={{ marginTop: 10 }}>
          What the posting is <span className="sf-cursive">really</span> asking for
        </h2>
        <p className="sf-lede">
          ApplyWise breaks the job into separate requirements so they can be matched against your
          evidence, one at a time.
        </p>
      </header>

      <div className="sf-side">
        <section className="sf-card">
          <div className="sf-row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
            <h3 className="sf-h3" style={{ margin: 0 }}>
              Paste the posting
            </h3>
            <span className="sf-muted">Stubbed until F04 merges</span>
          </div>

          <div className="sf-grid sf-grid-2">
            <label className="sf-field">
              <span>Job title</span>
              <input defaultValue="Software Engineer in Test" />
            </label>
            <label className="sf-field">
              <span>Company</span>
              <input defaultValue="Example Corp" />
            </label>
          </div>

          <label className="sf-field">
            <span>Description</span>
            <textarea
              value={text}
              onChange={(event) => {
                setText(event.target.value);
                setAnalysed(false);
              }}
              style={{ minHeight: 220 }}
            />
          </label>

          <button type="button" className="sf-btn sf-btn-primary" onClick={() => setAnalysed(true)}>
            {analysed ? "Re-analyse posting" : "Analyse posting"}
          </button>
        </section>

        <aside className="sf-stack">
          <div className="sf-card sf-card-lav">
            <h3 className="sf-h3">Extracted requirements</h3>
            <p className="sf-muted" style={{ margin: "0 0 14px" }}>
              {analysed ? `${REQUIREMENTS.length} found` : "Press analyse to refresh"}
            </p>
            {analysed &&
              REQUIREMENTS.map((requirement) => (
                <div key={requirement.name} style={{ marginBottom: 12 }}>
                  <span
                    className={
                      requirement.kind === "Required"
                        ? "sf-pill sf-pill-ok"
                        : "sf-pill sf-pill-quiet"
                    }
                  >
                    {requirement.kind}
                  </span>
                  <strong style={{ fontWeight: 500 }}>{requirement.name}</strong>
                </div>
              ))}
          </div>

          <div className="sf-banner sf-banner-ok">
            Requirements are text only. No resume content is written at this step.
          </div>

          <button type="button" className="sf-btn sf-btn-dark" onClick={() => go("match")}>
            See the match →
          </button>
        </aside>
      </div>
    </main>
  );
}

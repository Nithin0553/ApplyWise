import { useState } from "react";

import type { PageProps } from "../Shell";
import { REQUIREMENTS } from "../mock";

const POSTING = `We are hiring a Software Engineer in Test to own automated testing for a Python backend. You will design and maintain automated regression suites, work with engineers on release readiness, and improve our CI pipelines.

Required: 2+ years in software quality assurance, strong test automation experience, and familiarity with REST API testing.

Preferred: experience with performance testing, and exposure to Kubernetes in production.`;

/**
 * Requirements are grouped for reading, and a group with nothing in it is not
 * rendered at all — an empty "Preferred skills" heading tells the user nothing.
 */
const GROUPS = [
  { kind: "Required", title: "Required skills" },
  { kind: "Preferred", title: "Preferred skills" },
] as const;

export function JobsPage({ go }: PageProps) {
  const [text, setText] = useState(POSTING);
  const [analysed, setAnalysed] = useState(true);

  const groups = GROUPS.map((group) => ({
    ...group,
    items: REQUIREMENTS.filter((requirement) => requirement.kind === group.kind),
  })).filter((group) => group.items.length > 0);

  return (
    <main className="sf-page sf-reveal">
      <header className="sf-pagehead">
        <h2 className="sf-h2">Job analysis</h2>
        <p className="sf-lede">
          Paste a job description to break it into individual requirements, so they can be matched
          against your evidence.
        </p>
      </header>

      <div className="sf-side">
        <section className="sf-card" aria-labelledby="posting-heading">
          <h3 className="sf-h3" id="posting-heading" style={{ marginTop: 0 }}>
            Job description
          </h3>

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
            {analysed ? "Re-analyse description" : "Analyse description"}
          </button>
        </section>

        <aside className="sf-stack">
          <div className="sf-card" aria-labelledby="requirements-heading">
            <div className="sf-row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
              <h3 className="sf-h3" id="requirements-heading" style={{ margin: 0 }}>
                Requirements
              </h3>
              {analysed && <span className="sf-count">{REQUIREMENTS.length}</span>}
            </div>

            {!analysed ? (
              <p className="sf-muted" style={{ margin: "8px 0 0" }}>
                Analyse the description to see its requirements.
              </p>
            ) : groups.length === 0 ? (
              <p className="sf-muted" style={{ margin: "8px 0 0" }}>
                No requirements were found in this description.
              </p>
            ) : (
              groups.map((group) => (
                <div key={group.kind} className="sf-reqgroup">
                  <h4 className="sf-reqgroup__title">{group.title}</h4>
                  <ul className="sf-reqlist">
                    {group.items.map((requirement) => (
                      <li key={requirement.name}>{requirement.name}</li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </div>

          <p className="sf-muted" style={{ margin: 0, lineHeight: 1.6 }}>
            These requirements are used to evaluate and tailor your resume. Nothing is written to
            your resume at this step.
          </p>

          <button type="button" className="sf-btn sf-btn-dark" onClick={() => go("match")}>
            See the match
          </button>
        </aside>
      </div>
    </main>
  );
}

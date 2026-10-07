import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, fetchApprovedEvidence, generateStatements } from "../../features/tailoring/api";
import { AI_PROVIDERS, type AiProvider } from "../../features/tailoring/config";
import { MOCK_JOB_CONTEXT } from "../../features/tailoring/mockData";
import { useAuth } from "../../features/auth";
import type {
  EvidenceOption,
  GenerationResult,
} from "../../features/tailoring/types";
import type { PageProps } from "../Shell";

export function TailoringPage({ go }: PageProps) {
  const { token } = useAuth();
  const [evidence, setEvidence] = useState<EvidenceOption[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [jobTitle, setJobTitle] = useState(MOCK_JOB_CONTEXT.job_title);
  const [company, setCompany] = useState(MOCK_JOB_CONTEXT.company ?? "");
  const [description, setDescription] = useState(MOCK_JOB_CONTEXT.description);
  const [requirements, setRequirements] = useState(MOCK_JOB_CONTEXT.requirements.join(", "));
  const [provider, setProvider] = useState<AiProvider>("demo");
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchApprovedEvidence(token)
      .then((items) => {
        setEvidence(items);
        setSelectedIds(items.map((item) => item.evidence_id));
      })
      .catch((cause: unknown) =>
        setError(cause instanceof ApiError ? cause.message : "Could not load evidence."),
      );
  }, [token]);

  const selected = useMemo(
    () => evidence.filter((item) => selectedIds.includes(item.evidence_id)),
    [evidence, selectedIds],
  );

  const labels = useMemo(
    () => new Map(selected.map((item, index) => [item.evidence_id, `E${index + 1}`])),
    [selected],
  );

  const onGenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const statements = await generateStatements(
        {
          job_context: {
            job_title: jobTitle,
            company: company || null,
            description,
            requirements: requirements
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          },
          evidence_ids: selected.map((item) => item.evidence_id),
          max_statements: 5,
        },
        provider,
        token,
      );
      generated.current = true;
      setResult(statements);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Generation failed.");
    } finally {
      setLoading(false);
    }
  }, [selected, provider, jobTitle, company, description, requirements, token]);

  // After a first generation, switching provider redraws straight away rather
  // than leaving a stale result on screen under a new provider name.
  const generated = useRef(false);
  useEffect(() => {
    if (generated.current && selected.length > 0) {
      void onGenerate();
    }
  }, [provider]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <main className="sf-page sf-reveal">
      <header className="sf-pagehead">
        <h2 className="sf-h2">Tailored statements</h2>
        <p className="sf-lede">
          Each statement cites the approved evidence it rests on. Anything citing a source you did
          not supply is discarded before it reaches this page.
        </p>
      </header>

      <div className="sf-side">
        <section className="sf-stack">
          <div className="sf-card">
            <div className="sf-row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
              <h3 className="sf-h3" style={{ margin: 0 }}>
                Candidate statements
              </h3>
              <div className="sf-row" style={{ gap: 8 }}>
                <label className="sf-sr" htmlFor="provider">
                  AI provider
                </label>
                <select
                  id="provider"
                  value={provider}
                  onChange={(event) => setProvider(event.target.value as AiProvider)}
                  style={{
                    font: "inherit",
                    borderRadius: 999,
                    border: "1px solid #e7e5e4",
                    padding: "8px 14px",
                    background: "#ffffff",
                  }}
                >
                  {AI_PROVIDERS.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="sf-btn sf-btn-primary"
                  onClick={onGenerate}
                  disabled={loading || selected.length === 0}
                >
                  {loading ? "Generating…" : "Generate"}
                </button>
              </div>
            </div>

            {error && <div className="sf-banner sf-banner-stop">{error}</div>}
            {!result && !error && (
              <p className="sf-muted" style={{ margin: 0 }}>
                Pick your evidence and a job, then generate. Nothing is written until you ask.
              </p>
            )}

            {result?.statements.map((statement) => (
              <article
                key={statement.statement_id}
                style={{
                  borderTop: "1px solid #f5f5f4",
                  paddingTop: 16,
                  marginTop: 16,
                }}
              >
                <div style={{ marginBottom: 8 }}>
                  <span className="sf-pill sf-pill-cand">{statement.status}</span>
                  <span className="sf-pill sf-pill-quiet">
                    {statement.verification_status} verification
                  </span>
                  <span className="sf-pill sf-pill-quiet">Not exportable</span>
                </div>
                <p style={{ fontSize: 17, lineHeight: 1.6, margin: 0 }}>
                  {statement.text}{" "}
                  {statement.evidence_ids.map((id) => (
                    <span className="sf-chip" key={id} title={id}>
                      {labels.get(id) ?? "E?"}
                    </span>
                  ))}
                </p>
              </article>
            ))}
          </div>

          {result && result.rejected.length > 0 && (
            <div className="sf-card" style={{ background: "#f6ebe8" }}>
              <h3 className="sf-h3">Discarded before you saw them</h3>
              <p className="sf-muted" style={{ marginTop: 0 }}>
                The provider returned these. ApplyWise refused them.
              </p>
              {result.rejected.map((item, index) => (
                <article key={index} style={{ marginTop: 14 }}>
                  <span className="sf-pill sf-pill-stop">Rejected</span>
                  <p
                    style={{
                      margin: "8px 0 4px",
                      lineHeight: 1.6,
                      textDecoration: "line-through",
                      color: "#9a4034",
                    }}
                  >
                    {item.text}
                  </p>
                  <p className="sf-muted" style={{ margin: 0 }}>
                    Reason: {item.reason}
                  </p>
                </article>
              ))}
            </div>
          )}

          {result && (
            <div className="sf-banner sf-banner-ok">
              {result.statements.length} kept · {result.rejected.length} discarded · provider{" "}
              {result.provider}. Nothing here is verified or approved yet.
            </div>
          )}
        </section>

        <aside className="sf-stack">
          <div className="sf-card sf-card-sage">
            <h3 className="sf-h3">Evidence in play</h3>
            <p className="sf-muted" style={{ margin: "0 0 12px" }}>
              Select the approved evidence to draw on.
            </p>
            {evidence.map((item) => (
              <label className="sf-check" key={item.evidence_id} style={{ marginBottom: 10 }}>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(item.evidence_id)}
                  onChange={() =>
                    setSelectedIds((current) =>
                      current.includes(item.evidence_id)
                        ? current.filter((id) => id !== item.evidence_id)
                        : [...current, item.evidence_id],
                    )
                  }
                />
                <span>
                  {labels.has(item.evidence_id) && (
                    <span className="sf-chip">{labels.get(item.evidence_id)}</span>
                  )}
                  {item.title}
                </span>
              </label>
            ))}
          </div>

          <div className="sf-card">
            <h3 className="sf-h3">Target job</h3>
            <label className="sf-field">
              <span>Title</span>
              <input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} />
            </label>
            <label className="sf-field">
              <span>Company</span>
              <input value={company} onChange={(event) => setCompany(event.target.value)} />
            </label>
            <label className="sf-field">
              <span>Requirements (comma separated)</span>
              <input
                value={requirements}
                onChange={(event) => setRequirements(event.target.value)}
              />
            </label>
            <label className="sf-field">
              <span>Description</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </label>
            <p className="sf-muted" style={{ margin: 0 }}>
              Change the requirements and generate again — the statements reorder and reframe
              around them.
            </p>
          </div>

          <button type="button" className="sf-btn sf-btn-dark" onClick={() => go("review")}>
            Send to verification →
          </button>
        </aside>
      </div>
    </main>
  );
}

import { useEffect, useMemo, useState } from "react";

import { ApiError, fetchApprovedEvidence, generateStatements } from "./api";
import { AI_PROVIDERS, USE_REAL, type AiProvider } from "./config";
import { MOCK_JOB_CONTEXT } from "./mockData";
import { useAuth } from "../auth";
import "./tailoring.css";
import type { GenerationEvidence, GenerationResult } from "./types";

/** Short label (E1, E2, ...) for an evidence id, matching what the backend sends the provider. */
function refLabels(evidence: GenerationEvidence[]): Map<string, string> {
  return new Map(evidence.map((item, index) => [item.evidence_id, `E${index + 1}`]));
}

export function TailoringPage() {
  const { token } = useAuth();
  const [evidence, setEvidence] = useState<GenerationEvidence[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [jobTitle, setJobTitle] = useState(MOCK_JOB_CONTEXT.job_title);
  const [company, setCompany] = useState(MOCK_JOB_CONTEXT.company ?? "");
  const [description, setDescription] = useState(MOCK_JOB_CONTEXT.description);
  const [provider, setProvider] = useState<AiProvider>("demo");
  const [maxStatements, setMaxStatements] = useState(5);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchApprovedEvidence()
      .then((items) => {
        setEvidence(items);
        setSelectedIds(items.map((item) => item.evidence_id));
      })
      .catch((cause: unknown) => {
        setError(cause instanceof ApiError ? cause.message : "Could not load evidence.");
      });
  }, []);

  const selected = useMemo(
    () => evidence.filter((item) => selectedIds.includes(item.evidence_id)),
    [evidence, selectedIds],
  );
  const labels = useMemo(() => refLabels(selected), [selected]);

  function toggle(id: string) {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  }

  async function onGenerate() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const generated = await generateStatements(
        {
          job_context: {
            job_title: jobTitle,
            company: company || null,
            description,
            requirements: MOCK_JOB_CONTEXT.requirements,
          },
          approved_evidence: selected,
          max_statements: maxStatements,
        },
        provider,
        token,
      );
      setResult(generated);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Generation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="tailoring">
      <div>
        <div className="card">
          <h2>Approved evidence</h2>
          <p className="source-note">
            {USE_REAL.f02_evidence
              ? "Loaded from the evidence service (F02)."
              : "Stubbed: F02 is not merged yet, so this list stands in for approved evidence."}
          </p>
          {evidence.map((item) => (
            <div className="evidence-item" key={item.evidence_id}>
              <input
                type="checkbox"
                id={`ev-${item.evidence_id}`}
                checked={selectedIds.includes(item.evidence_id)}
                onChange={() => toggle(item.evidence_id)}
              />
              <div>
                <label htmlFor={`ev-${item.evidence_id}`}>
                  {labels.has(item.evidence_id) && (
                    <span className="chip">{labels.get(item.evidence_id)}</span>
                  )}
                  <strong>{item.title}</strong>
                </label>
                <div className="meta">
                  {item.evidence_type}
                  {item.organization ? ` · ${item.organization}` : ""}
                </div>
                {item.description && <div className="meta">{item.description}</div>}
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <h2>Target job</h2>
          <label className="field">
            <span>Job title</span>
            <input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} />
          </label>
          <label className="field">
            <span>Company</span>
            <input value={company} onChange={(event) => setCompany(event.target.value)} />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
        </div>
      </div>

      <div>
        <div className="toolbar">
          <label className="field">
            <span>AI provider</span>
            <select
              value={provider}
              onChange={(event) => setProvider(event.target.value as AiProvider)}
            >
              {AI_PROVIDERS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Max statements</span>
            <input
              type="number"
              min={1}
              max={10}
              value={maxStatements}
              onChange={(event) => setMaxStatements(Number(event.target.value))}
            />
          </label>
          <button
            type="button"
            className="primary"
            onClick={onGenerate}
            disabled={loading || selected.length === 0}
          >
            {loading ? "Generating…" : "Generate statements"}
          </button>
        </div>

        {selected.length === 0 && (
          <div className="banner banner-info">
            Select at least one evidence item. Generation without evidence is refused by the
            contract.
          </div>
        )}
        {error && <div className="banner banner-error">{error}</div>}

        {result && (
          <>
            <div className="banner banner-info">
              {result.statements.length} candidate statement
              {result.statements.length === 1 ? "" : "s"} · {result.rejected.length} rejected ·
              provider: {result.provider}
            </div>

            <div className="card">
              <h2>Candidate statements</h2>
              {result.statements.length === 0 && (
                <p className="source-note">
                  Nothing survived validation. Every statement the provider returned was
                  ungrounded.
                </p>
              )}
              {result.statements.map((statement) => (
                <article className="statement" key={statement.statement_id}>
                  <div>
                    <span className="pill pill-candidate">{statement.status}</span>
                    <span className="pill pill-muted">
                      {statement.verification_status} VERIFICATION
                    </span>
                    <span className="pill pill-muted">NOT EXPORTABLE</span>
                  </div>
                  <p>
                    {statement.text}{" "}
                    {statement.evidence_ids.map((id) => (
                      <span className="chip" key={id} title={id}>
                        {labels.get(id) ?? "E?"}
                      </span>
                    ))}
                  </p>
                </article>
              ))}
            </div>

            {result.rejected.length > 0 && (
              <div className="card">
                <h2>Rejected by ApplyWise</h2>
                {result.rejected.map((item, index) => (
                  <article className="statement statement-rejected" key={index}>
                    <div>
                      <span className="pill pill-rejected">REJECTED</span>
                    </div>
                    <p>{item.text}</p>
                    <p className="reason">Reason: {item.reason}</p>
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

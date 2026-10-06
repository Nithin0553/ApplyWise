import { useState } from "react";
import type { AnalysisResult, Requirement } from "./contract";
import "./job-analysis.css";

const sample = `Software Engineer
Required qualifications:
- Proficiency in Python and SQL.
- Bachelor's degree in computer science or equivalent experience.
- At least 3 years of software development experience.
Preferred skills:
- Familiarity with AWS.
Optional skills:
- Knowledge of Docker.
Responsibilities:
- Build and maintain REST APIs.`;

export function JobAnalysisPage() {
  const [text, setText] = useState("");
  const [source, setSource] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [selected, setSelected] = useState<Requirement | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function analyze() {
    setBusy(true); setError(""); setResult(null); setSelected(null);
    const submitted = text;
    try {
      const response = await fetch("/api/f04/analyze", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: submitted }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail = typeof data.detail === "string" ? data.detail
          : Array.isArray(data.detail) ? data.detail.map((d: { msg: string }) => d.msg).join("; ")
          : "The job description could not be analyzed.";
        throw new Error(detail);
      }
      setSource(submitted); setResult(data as AnalysisResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed. Check that the local API is running.");
    } finally { setBusy(false); }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = "job-requirements.json";
    link.click(); URL.revokeObjectURL(url);
  }
  return <main className="job-analysis">
    <header><p className="eyebrow">APPLYWISE · F04 PROTOTYPE</p>
      <h1>Understand the job requirements</h1>
      <p>Extract requirements, check their source, and pass structured results to matching.</p>
    </header>
    <p className="prototype">Local, rule-based English prototype. Review results before using them for matching. No account or persistence is connected.</p>
    <form onSubmit={e => { e.preventDefault(); void analyze(); }}>
      <label htmlFor="description">Job description</label>
      <textarea id="description" required maxLength={50000} rows={12} value={text}
        onChange={e => setText(e.target.value)} placeholder="Paste a plain-text job posting, including requirements and responsibilities." />
      <div className="actions"><button disabled={busy || !text.trim()}>{busy ? "Analyzing…" : "Analyze requirements"}</button>
        <button type="button" className="secondary" disabled={busy} onClick={() => setText(sample)}>Load sample posting</button></div>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    {result && <section aria-labelledby="results-heading">
      <div className="results-title"><h2 id="results-heading">Extracted requirements</h2>
        <button type="button" className="secondary" onClick={download}>Download JSON</button></div>
      <p role="status">{result.requirements.length} requirements · {result.requirements.filter(r => r.needs_review).length} need review</p>
      {text !== source && <p className="prototype">The input has changed. Analyze again to update these results.</p>}
      {result.warnings.map(w => <p key={w} className="warning">{w}</p>)}
      <div className="requirements">{result.requirements.map(r => <article key={r.id}>
        <div className="tags"><span>{r.importance ?? "Importance unspecified"}</span><span>{r.categories.join(" · ")}</span></div>
        <h3>{r.text}</h3>
        <p>Source: line {r.source.line}{r.source.section ? ` · ${r.source.section}` : ""}</p>
        {r.experience && <p>Experience: {r.experience.expression}</p>}
        {r.review_reasons.length > 0 && <ul>{r.review_reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>}
        <button type="button" className="secondary" onClick={() => setSelected(r)}>View source for line {r.source.line}</button>
      </article>)}</div>
      {selected && <section className="source-panel" aria-label="Source context">
        <h3>Original source · line {selected.source.line}</h3>
        <p>{selected.source.text}</p>
        <p>Character offsets: {selected.source.start}–{selected.source.end} (end excluded).</p>
        <button type="button" className="secondary" onClick={() => setSelected(null)}>Close source</button>
      </section>}
    </section>}
  </main>;
}

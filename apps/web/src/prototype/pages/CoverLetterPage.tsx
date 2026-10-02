import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { generateCoverLetter, type CoverLetterDraft } from "../../features/cover-letter/api";
import { ApiError } from "../../features/tailoring/api";
import { AI_PROVIDERS, type AiProvider } from "../../features/tailoring/config";
import { MOCK_JOB_CONTEXT } from "../../features/tailoring/mockData";
import type { PageProps } from "../Shell";
import { toApprovedStatements, useApprovals } from "../store";

const DEMO_USER_ID = "00000000-0000-0000-0000-0000000000aa";
const TONES = ["professional", "warm", "direct"] as const;

/** Scaffolding lines: part of the letter, but not AI-generated content. */
const SCAFFOLD_STYLE = {
  fontSize: 17,
  lineHeight: 1.7,
  margin: 0,
  color: "#78716c",
  borderLeft: "2px dashed #e7e5e4",
  paddingLeft: 14,
} as const;

export function CoverLetterPage({ go }: PageProps) {
  const { approvedIds } = useApprovals();
  const approvedStatements = useMemo(() => toApprovedStatements(approvedIds), [approvedIds]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [tone, setTone] = useState<(typeof TONES)[number]>("professional");
  const [provider, setProvider] = useState<AiProvider>("demo");
  const [draft, setDraft] = useState<CoverLetterDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Default to every approved statement, and follow changes made on Review.
  useEffect(() => {
    setSelectedIds(approvedStatements.map((item) => item.statement_id));
  }, [approvedStatements]);

  const selected = useMemo(
    () => approvedStatements.filter((item) => selectedIds.includes(item.statement_id)),
    [approvedStatements, selectedIds],
  );

  const labels = useMemo(
    () => new Map(selected.map((item, index) => [item.statement_id, `S${index + 1}`])),
    [selected],
  );

  const onGenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setDraft(null);
    try {
      drafted.current = true;
      setDraft(
        await generateCoverLetter(
          {
            user_id: DEMO_USER_ID,
            job_context: MOCK_JOB_CONTEXT,
            approved_statements: selected,
            tone,
            max_paragraphs: 3,
          },
          provider,
        ),
      );
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Drafting failed.");
    } finally {
      setLoading(false);
    }
  }, [selected, tone, provider]);

  // Once a draft exists, changing the tone or the statements redraws it, so the
  // controls are not silently ignored.
  const drafted = useRef(false);
  useEffect(() => {
    if (drafted.current && selected.length > 0) {
      void onGenerate();
    }
  }, [tone, provider]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <main className="sf-page sf-reveal">
      <header style={{ marginBottom: 28 }}>
        <p className="sf-eyebrow">F11 · Cover letter · live</p>
        <h2 className="sf-h2" style={{ marginTop: 10 }}>
          A letter built only from what you already <span className="sf-cursive">approved</span>
        </h2>
        <p className="sf-lede">
          F11 starts where F09 ends. It drafts from approved statements, keeps each paragraph tied
          to its sources, and still produces candidates — approving a statement never
          auto-approves a paragraph written from it.
        </p>
      </header>

      <div className="sf-side">
        <section className="sf-stack">
          <div className="sf-card">
            <div className="sf-row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
              <h3 className="sf-h3" style={{ margin: 0 }}>
                Draft
              </h3>
              <button
                type="button"
                className="sf-btn sf-btn-primary"
                onClick={onGenerate}
                disabled={loading || selected.length === 0}
              >
                {loading ? "Drafting…" : "Draft letter"}
              </button>
            </div>

            {error && <div className="sf-banner sf-banner-stop">{error}</div>}
            {!draft && !error && !loading && (
              <p className="sf-muted" style={{ margin: 0 }}>
                No letter yet. Pick the statements to draw on, choose a tone, then press
                <strong> Draft letter</strong>.
              </p>
            )}

            {draft && (
              <div style={{ marginTop: 16 }}>
                {/* Greeting and sign-off are document scaffolding owned by the
                    template (F10), not generated content. They make no claim
                    about the applicant, so they carry no citation — and F11
                    would reject them if a provider tried to write them. */}
                <p style={SCAFFOLD_STYLE}>
                  <span className="sf-pill sf-pill-quiet">Template</span>
                  Dear Hiring Team,
                </p>

                {draft.paragraphs.map((paragraph) => (
                  <article key={paragraph.paragraph_id} style={{ margin: "18px 0" }}>
                    <div style={{ marginBottom: 8 }}>
                      <span className="sf-pill sf-pill-cand">{paragraph.status}</span>
                      <span className="sf-pill sf-pill-quiet">
                        {paragraph.verification_status} verification
                      </span>
                      <span className="sf-pill sf-pill-quiet">Not exportable</span>
                    </div>
                    <p style={{ fontSize: 17, lineHeight: 1.7, margin: 0 }}>{paragraph.text}</p>
                    <p className="sf-muted" style={{ margin: "10px 0 0" }}>
                      From{" "}
                      {paragraph.statement_ids.map((id) => (
                        <span className="sf-chip" key={id} title={id}>
                          {labels.get(id) ?? "S?"}
                        </span>
                      ))}
                      · {paragraph.evidence_ids.length} evidence item
                      {paragraph.evidence_ids.length === 1 ? "" : "s"} behind it
                    </p>
                  </article>
                ))}

                <p style={SCAFFOLD_STYLE}>
                  <span className="sf-pill sf-pill-quiet">Template</span>
                  Sincerely,
                  <br />
                  Niraali Deepak Bandi
                </p>

                <p className="sf-muted" style={{ margin: "16px 0 0", lineHeight: 1.6 }}>
                  The greeting and sign-off come from the document template, not from the AI.
                  They state nothing about you, so they need no evidence — and F11 would reject
                  them if a provider tried to write them, because they cite no approved
                  statement.
                </p>
              </div>
            )}
          </div>

          {draft && draft.rejected.length > 0 && (
            <div className="sf-card" style={{ background: "#fdf6f5" }}>
              <h3 className="sf-h3">Discarded before you saw them</h3>
              {draft.rejected.map((item, index) => (
                <article key={index} style={{ marginTop: 14 }}>
                  <span className="sf-pill sf-pill-stop">Rejected</span>
                  <p
                    style={{
                      margin: "8px 0 4px",
                      lineHeight: 1.6,
                      textDecoration: "line-through",
                      color: "#8a3a33",
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
        </section>

        <aside className="sf-stack">
          <div className="sf-card sf-card-sage">
            <h3 className="sf-h3">Approved statements</h3>
            <p className="sf-muted" style={{ margin: "0 0 12px" }}>
              These come from what you approved on the Review screen. Unsupported statements
              never appear here — the contract refuses them, not the screen.
            </p>
            {approvedStatements.length === 0 && (
              <p className="sf-muted">
                Nothing approved yet. Approve statements on the Review screen first.
              </p>
            )}
            {approvedStatements.map((item) => (
              <label className="sf-check" key={item.statement_id} style={{ marginBottom: 12 }}>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(item.statement_id)}
                  onChange={() =>
                    setSelectedIds((current) =>
                      current.includes(item.statement_id)
                        ? current.filter((id) => id !== item.statement_id)
                        : [...current, item.statement_id],
                    )
                  }
                />
                <span>
                  {labels.has(item.statement_id) && (
                    <span className="sf-chip">{labels.get(item.statement_id)}</span>
                  )}
                  <span
                    className={
                      item.verification_status === "VERIFIED"
                        ? "sf-pill sf-pill-ok"
                        : "sf-pill sf-pill-warn"
                    }
                  >
                    {item.verification_status}
                  </span>
                  <span style={{ display: "block", marginTop: 4 }}>{item.text}</span>
                </span>
              </label>
            ))}
          </div>

          <div className="sf-card">
            <h3 className="sf-h3">Tone</h3>
            <p className="sf-muted" style={{ margin: "0 0 12px" }}>
              Changes the wording only. The statements used, and the evidence behind them, stay
              the same — tone must never change what you are claiming.
            </p>
            <div className="sf-row" style={{ gap: 8 }}>
              {TONES.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={tone === option ? "sf-btn sf-btn-dark" : "sf-btn sf-btn-ghost"}
                  onClick={() => setTone(option)}
                >
                  {option}
                </button>
              ))}
            </div>
            <label className="sf-field" style={{ marginTop: 16 }}>
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
          </div>

          {draft && draft.paragraphs.length > 0 && (
            <div className="sf-banner sf-banner-warn">
              These paragraphs are new prose, so they need their own verification and approval
              before export. That step is F08/F09 work and is not wired up in this prototype.
            </div>
          )}
          <button type="button" className="sf-btn sf-btn-ghost" onClick={() => go("review")}>
            ← Back to approved statements
          </button>
        </aside>
      </div>
    </main>
  );
}

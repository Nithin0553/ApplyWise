import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import type { User } from "../auth/types";
import type { CandidateStatement } from "../tailoring/types";
import {
  addEvidence, approveEvidenceItem, downloadReviewedText, estimateOverlap,
  generateCandidates, getApplications, getEvidence, getVersions,
  readRequirements, saveReviewedResume,
  type JourneyApplication, type JourneyEvidence,
} from "./api";
import "./journey.css";

interface Props { user: User; token: string; logout: () => void }
type Stage = "setup" | "preparing" | "ready" | "paste" | "analyzing" | "analysis" |
  "generating" | "resume" | "exporting" | "applications";
interface Profile {
  career: string; years: string; arrangement: string; focus: string[];
  experience: string; resumeName: string;
}
const INITIAL: Profile = { career: "", years: "", arrangement: "", focus: [], experience: "", resumeName: "" };
const CAREERS = ["Software Engineer", "Data Analyst", "QA / Test Engineer", "Product Manager", "Designer", "Business Analyst", "Other"];
const YEARS = ["Student / New graduate", "0–2 years", "3–5 years", "6–10 years", "10+ years"];
const ARRANGEMENTS = ["Remote", "Hybrid", "On-site", "Open to any"];
const FOCUS = ["Python", "JavaScript", "SQL", "Testing", "Cloud", "Design", "Leadership", "Research"];
function localProfileKey(id: string) { return `applywise.journey.profile.${id}`; }
function readProfile(id: string): Profile | null {
  try {
    const raw = localStorage.getItem(localProfileKey(id));
    if (!raw) return null;
    const value = JSON.parse(raw) as Profile;
    return value && typeof value.career === "string" && value.career ? value : null;
  } catch { return null; }
}
const delay = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

function Onboarding({
  profile, setProfile, finish, busy,
}: {
  profile: Profile;
  setProfile: (next: Profile) => void;
  finish: () => void;
  busy: boolean;
}) {
  const [question, setQuestion] = useState(0);
  const [customRole, setCustomRole] = useState("");
  const liveRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (question > 0 && liveRef.current && "scrollIntoView" in liveRef.current) {
      liveRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [question]);
  const valid = [
    !!profile.career, !!profile.years, !!profile.arrangement, profile.focus.length > 0,
    !!profile.experience.trim(), true,
  ];
  const prompts = [
    "What kind of role are you looking for?",
    "How much professional experience do you have?",
    "How would you like to work?",
    "What are your strongest skills?",
    "Tell us what you've actually done.",
    "Finally, select your previous resume.",
  ];
  function set<K extends keyof Profile>(key: K, value: Profile[K]) {
    setProfile({ ...profile, [key]: value });
  }
  return (
    <main className="aw-onboarding">
      <div className="aw-eyebrow">A LITTLE ABOUT YOU</div>
      <h2>Your story comes first.</h2>
      <p className="aw-muted">Answer a few questions. Each answer helps shape your workspace.</p>
      <div className="aw-progress"><span style={{ width: `${(question + 1) / 6 * 100}%` }} /></div>
      {prompts.slice(0, question + 1).map((prompt, i) => (
        <section className={`aw-question ${i === question ? "is-current" : "is-complete"}`}
          key={prompt} ref={i === question ? liveRef : undefined}>
          <div className="aw-question-count">0{i + 1} / 06</div>
          <h3>{prompt}</h3>
          {i < question ? (
            <p className="aw-answer-summary">
              {i === 0 ? profile.career : i === 1 ? profile.years : i === 2 ? profile.arrangement :
                i === 3 ? profile.focus.join(", ") : i === 4 ? profile.experience : profile.resumeName || "Not selected"}
            </p>
          ) : (
            <>
              {i === 0 && <>
                <div className="aw-choices">{CAREERS.map((value) =>
                  <button type="button" key={value}
                    className={profile.career === value ? "selected" : ""}
                    onClick={() => set("career", value)}>{value}</button>)}</div>
                {profile.career === "Other" && <input className="aw-text-field" aria-label="Your target role"
                  placeholder="Your target role" value={customRole}
                  onChange={(event) => setCustomRole(event.target.value)} />}
              </>}
              {i === 1 && <div className="aw-choices">{YEARS.map((value) =>
                <button key={value} type="button" className={profile.years === value ? "selected" : ""}
                  onClick={() => set("years", value)}>{value}</button>)}</div>}
              {i === 2 && <div className="aw-choices">{ARRANGEMENTS.map((value) =>
                <button key={value} type="button" className={profile.arrangement === value ? "selected" : ""}
                  onClick={() => set("arrangement", value)}>{value}</button>)}</div>}
              {i === 3 && <div className="aw-choices">{FOCUS.map((value) =>
                <button key={value} type="button" className={profile.focus.includes(value) ? "selected" : ""}
                  aria-pressed={profile.focus.includes(value)}
                  onClick={() => set("focus", profile.focus.includes(value)
                    ? profile.focus.filter((skill) => skill !== value) : [...profile.focus, value])}>{value}</button>)}</div>}
              {i === 4 && <>
                <p className="aw-muted">Describe a project, job, or accomplishment in your own words. You will review it as evidence before it can be used.</p>
                <textarea className="aw-text-field" aria-label="Your real experience" rows={4}
                  placeholder="For example: Developed API tests in Python for an internship project..."
                  value={profile.experience} onChange={(event) => set("experience", event.target.value)} />
              </>}
              {i === 5 && <>
                <label className="aw-file-select" htmlFor="aw-resume-upload">
                  <span aria-hidden="true">↑</span> {profile.resumeName || "Choose resume file"}
                  <input id="aw-resume-upload" type="file" accept=".pdf,.doc,.docx,.txt"
                    onChange={(event) => set("resumeName", event.target.files?.[0]?.name ?? "")} />
                </label>
                <p className="aw-muted">Optional. The file stays on your device; resume importing is not yet connected. We record only its name in this browser.</p>
              </>}
              <button className="aw-primary aw-next" type="button"
                disabled={busy || !valid[i] || (i === 0 && profile.career === "Other" && !customRole.trim())}
                onClick={() => {
                  if (i === 0 && profile.career === "Other") set("career", customRole.trim());
                  if (i < 5) setQuestion(i + 1);
                  else finish();
                }}>
                {i === 5 ? "Finish setup" : "Continue"} <span aria-hidden="true">→</span>
              </button>
            </>
          )}
        </section>
      ))}
    </main>
  );
}

function Spinner({ title, description }: { title: string; description: string }) {
  return <main className="aw-center-state aw-fade" role="status">
    <div className="aw-spinner" aria-hidden="true" />
    <h2>{title}</h2><p>{description}</p>
  </main>;
}

export function GuidedJourney({ user, token, logout }: Props) {
  const stored = readProfile(user.id);
  const [profile, setProfile] = useState<Profile>(stored ?? INITIAL);
  const [stage, setStage] = useState<Stage>(stored ? "paste" : "setup");
  const [job, setJob] = useState("");
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [requirements, setRequirements] = useState<string[]>([]);
  const [evidence, setEvidence] = useState<JourneyEvidence[]>([]);
  const [candidates, setCandidates] = useState<CandidateStatement[]>([]);
  const [approvedIds, setApprovedIds] = useState<string[]>([]);
  const [deniedIds, setDeniedIds] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [savedApplications, setSavedApplications] = useState<JourneyApplication[]>([]);
  const [versionCounts, setVersionCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (stage !== "ready") return;
    const t = window.setTimeout(() => setStage("paste"), 1500);
    return () => window.clearTimeout(t);
  }, [stage]);

  function changeStage(next: Stage) {
    setError("");
    setSelectedId(null);
    setStage(next);
    window.scrollTo?.({ top: 0, behavior: "smooth" });
  }

  async function finishSetup() {
    setBusy(true); setError(""); setStage("preparing");
    try {
      if (profile.experience.trim()) {
        await addEvidence(token, `${profile.career} experience`, profile.career,
          profile.experience.trim());
      }
      localStorage.setItem(localProfileKey(user.id), JSON.stringify(profile));
      await delay(750);
      setStage("ready");
    } catch (err) {
      setStage("setup");
      setError(err instanceof Error ? err.message : "Could not save evidence. Please retry.");
    } finally { setBusy(false); }
  }

  async function analyzeJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!job.trim()) return;
    setError(""); setStage("analyzing");
    const lines = job.trim().split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const first = lines[0]?.replace(/^job title:\s*/i, "").slice(0, 120) ?? "";
    setRole((current) => current || (first.length < 90 ? first : profile.career));
    const reqs = readRequirements(job);
    try {
      const [records] = await Promise.all([getEvidence(token), delay(850)]);
      setEvidence(records);
      setRequirements(reqs);
      setStage("analysis");
    } catch (err) {
      setStage("paste");
      setError(err instanceof Error ? err.message : "Could not load your evidence.");
    }
  }

  async function approve(item: JourneyEvidence) {
    setBusy(true); setError("");
    try {
      const result = await approveEvidenceItem(token, item.id);
      setEvidence((current) => current.map((record) => record.id === item.id ? result : record));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not approve evidence."); }
    finally { setBusy(false); }
  }

  async function generateResume() {
    const available = evidence.filter((item) => item.status === "approved");
    if (!available.length) return;
    setStage("generating"); setError("");
    try {
      const result = await generateCandidates(token, {
        role: role.trim() || profile.career, company: company.trim(),
        description: job, requirements,
      }, available.map((item) => item.id));
      if (!result.statements.length) throw new Error("No grounded statements were returned. Add more approved evidence.");
      setCandidates(result.statements);
      setApprovedIds([]); setDeniedIds([]);
      await delay(500);
      setStage("resume");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume generation could not complete.");
      setStage("analysis");
    }
  }

  async function openApplications() {
    setError(""); setStage("applications");
    try {
      const apps = await getApplications(token);
      setSavedApplications(apps.slice().reverse());
      const totals = await Promise.all(apps.slice(-15).map(async (app) => {
        try { return [app.id, (await getVersions(token, app.id)).length] as const; }
        catch { return [app.id, 0] as const; }
      }));
      setVersionCounts(Object.fromEntries(totals));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load applications."); }
  }

  async function exportReviewed() {
    const approved = candidates.filter((item) => approvedIds.includes(item.statement_id));
    if (!approved.length || candidates.some((item) => !approvedIds.includes(item.statement_id) && !deniedIds.includes(item.statement_id))) return;
    setBusy(true); setError("");
    try {
      await saveReviewedResume(token, { role, company, description: job }, evidence, approved);
      downloadReviewedText(user.full_name, { role, company }, approved);
      setStage("exporting");
      await delay(1200);
      await openApplications();
    } catch (err) {
      setStage("resume");
      setError(err instanceof Error ? err.message : "Could not save the reviewed resume.");
    } finally { setBusy(false); }
  }

  const activeCandidates = candidates.filter((item) => !deniedIds.includes(item.statement_id));
  const pendingCount = candidates.filter((item) => !approvedIds.includes(item.statement_id) && !deniedIds.includes(item.statement_id)).length;
  const approvedEvidence = evidence.filter((item) => item.status === "approved");
  const match = estimateOverlap(requirements, approvedEvidence);
  const initials = user.full_name.trim().split(/\s+/).slice(0, 2).map((x) => x[0]?.toUpperCase()).join("") || "?";

  return <div className="aw-journey">
    <header className="aw-topbar">
      <button className="aw-logo" type="button" onClick={() => changeStage("paste")}>ApplyWise</button>
      <nav className="aw-toplinks" aria-label="Your workspace">
        <button type="button" onClick={() => changeStage("paste")}>New job</button>
        <button type="button" onClick={() => void openApplications()}>Applications</button>
        <div className="aw-avatar" title={user.full_name}>{initials}</div>
        <details className="aw-account"><summary>Profile</summary>
          <div className="aw-account-popup"><strong>{user.full_name}</strong><span>{user.email}</span>
            <button type="button" onClick={() => changeStage("setup")}>Edit profile</button></div>
        </details>
        <button type="button" onClick={logout}>Log out</button>
      </nav>
    </header>

    {error && <div className="aw-error" role="alert">{error}</div>}

    {stage === "setup" && <Onboarding profile={profile} setProfile={setProfile} finish={() => void finishSetup()} busy={busy} />}
    {stage === "preparing" && <Spinner title="Preparing your workspace…" description="Saving the experience you shared as evidence for your review." />}
    {stage === "ready" && <main className="aw-center-state aw-fade" role="status">
      <div className="aw-done-circle" aria-hidden="true">✓</div>
      <h2>All set.</h2><p>Your workspace is ready.</p>
    </main>}

    {stage === "paste" && <main className="aw-paste aw-fade">
      <form onSubmit={(e) => void analyzeJob(e)}>
        <h2>Paste your job description to <span className="aw-shine">ApplyWise</span></h2>
        <div className="aw-input-glow">
          <textarea aria-label="Paste your job description to ApplyWise" value={job}
            maxLength={6000} onChange={(e) => setJob(e.target.value)}
            placeholder="Paste the full job description here..." />
          <span className="aw-counter">{job.length} / 6000</span>
        </div>
        <p className="aw-privacy">♙ Your job description is used for this application workflow.</p>
        <div className="aw-actions">
          <button className="aw-primary" type="submit" disabled={!job.trim()}>Continue →</button>
          <button type="button" className="aw-link" disabled={!job} onClick={() => setJob("")}>Clear</button>
        </div>
        <p className="aw-tip">✦ <strong>Tip:</strong> Include the full role summary, responsibilities and requirements for better tailoring.</p>
      </form>
    </main>}
    {stage === "analyzing" && <Spinner title="Reading the job description…" description="Finding requirements and comparing them with approved evidence." />}

    {stage === "analysis" && <main className="aw-workspace aw-fade">
      <div className="aw-eyebrow">JOB ANALYSIS</div>
      <h2>Here's what the role asks for.</h2>
      <p className="aw-muted">Requirements are extracted from your posting with a simple text parser. Please review them.</p>
      <div className="aw-edit-job">
        <label>Job title<input value={role} onChange={(e) => setRole(e.target.value)} maxLength={200} /></label>
        <label>Company<input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Company name (optional)" maxLength={200} /></label>
      </div>
      <div className="aw-analysis-grid">
        <section className="aw-panel aw-stagger">
          <h3>Job details</h3>
          <p className="aw-muted">{requirements.length} extracted requirements</p>
          {requirements.length ? requirements.map((r, i) =>
            <div className="aw-result-row" key={i} style={{ animationDelay: `${i * 100}ms` }}>
              <span className="aw-small-index">{String(i + 1).padStart(2, "0")}</span>{r}
            </div>) : <p>No distinct requirements were found. You can still use the full posting for generation.</p>}
        </section>
        <section className="aw-panel aw-stagger">
          <h3>Evidence match</h3>
          <div className="aw-match-circle" style={{ "--percent": `${match.percentage}%` } as CSSProperties}>
            <strong>{match.percentage}%</strong>
          </div>
          <p className="aw-muted aw-center">Estimated keyword overlap only — not a verified match or ATS score.</p>
          <div className="aw-evidence-list">
            {evidence.length ? evidence.map((item) =>
              <article className="aw-evidence-row" key={item.id}>
                <div><strong>{item.title}</strong><small>{item.description || item.role || "Evidence item"}</small></div>
                {item.status === "approved" ? <span className="aw-approved">Approved</span> :
                  <button type="button" disabled={busy} onClick={() => void approve(item)}>Review & approve</button>}
              </article>) : <p className="aw-muted">No evidence saved yet. Add an example of your own work below.</p>}
          </div>
          <details className="aw-add-evidence"><summary>+ Add your own evidence</summary>
            <form onSubmit={async (e) => {
              e.preventDefault();
              const form = e.currentTarget;
              const data = new FormData(form);
              const summary = String(data.get("summary") ?? "").trim();
              const title = String(data.get("title") ?? "").trim();
              if (!summary || !title) return;
              setBusy(true); setError("");
              try { const item = await addEvidence(token, title, role, summary); setEvidence((current) => [...current, item]); form.reset(); }
              catch (err) { setError(err instanceof Error ? err.message : "Could not add evidence."); }
              finally { setBusy(false); }
            }}>
              <input name="title" required maxLength={200} placeholder="Project or experience title" aria-label="Evidence title" />
              <textarea name="summary" required placeholder="What did you actually do?" aria-label="Evidence description" />
              <button type="submit" disabled={busy}>Add for review</button>
            </form>
          </details>
        </section>
      </div>
      <div className="aw-section-bottom"><button className="aw-primary" type="button"
        onClick={() => void generateResume()} disabled={approvedEvidence.length === 0}>
        Generate resume →</button>
        {!approvedEvidence.length && <p className="aw-muted">Approve at least one real evidence item before generating.</p>}
        <p className="aw-muted">Generation uses the scripted grounded provider. Every line remains a candidate until you review it.</p>
      </div>
    </main>}
    {stage === "generating" && <Spinner title="Preparing your resume…" description="Generating candidate statements from your approved evidence. No claims are automatically approved." />}

    {(stage === "resume" || stage === "exporting") && <main className={`aw-resume-stage aw-fade ${stage === "exporting" ? "aw-exporting" : ""}`}>
      <div className="aw-eyebrow">RESUME STUDIO</div>
      <h2>Make every line yours.</h2>
      <p className="aw-muted">Select a highlighted statement to see its evidence. Approve or deny each candidate.</p>
      <article className={`aw-document ${selectedId ? "aw-document-dim" : ""}`}>
        <header><h3>{user.full_name}</h3><p>{role}{company ? ` · ${company}` : ""}</p></header>
        <div className="aw-document-rule" />
        <h4>Relevant experience</h4>
        {activeCandidates.map((item, index) => {
          const approved = approvedIds.includes(item.statement_id);
          const selected = selectedId === item.statement_id;
          const citations = evidence.filter((record) => item.evidence_ids.includes(record.id));
          return <div key={item.statement_id}
            className={`aw-document-line ${approved ? "is-approved" : "needs-review"} ${selected ? "is-selected" : ""}`}
            style={{ animationDelay: `${index * 165}ms` }}>
            {approved ? <p className="aw-approved-line">✓ {item.text}</p> :
              <button type="button" className="aw-line-preview" aria-expanded={selected}
                onClick={() => setSelectedId(selected ? null : item.statement_id)}>
                <span>{item.text}</span><small>{selected ? "Close" : "Review this line ↗"}</small>
              </button>}
            {selected && !approved && <div className="aw-line-detail">
              <p><strong>Evidence used</strong></p>
              {citations.map((ev) => <p key={ev.id}><b>{ev.title}:</b> {ev.description || ev.role || ev.title}</p>)}
              <p className="aw-review-note">Verify every claim yourself. Automatic F08 verification is not available.</p>
              <div className="aw-review-actions">
                <button type="button" onClick={() => { setDeniedIds((a) => [...a, item.statement_id]); setSelectedId(null); }}>Deny</button>
                <button type="button" onClick={() => { setApprovedIds((a) => [...a, item.statement_id]); setSelectedId(null); }}>I verified this — Approve</button>
              </div>
            </div>}
          </div>;
        })}
        {!activeCandidates.length && <p>No statements left. Return to analysis to generate another version.</p>}
      </article>
      <div className="aw-section-bottom">
        <p className="aw-muted">{pendingCount} statements awaiting review · {approvedIds.length} approved</p>
        <button type="button" className="aw-primary"
          disabled={busy || pendingCount !== 0 || approvedIds.length === 0}
          onClick={() => void exportReviewed()}>
          Save to applications & download →</button>
        <p className="aw-muted">Downloads a reviewed text resume (.txt) and saves an F13 snapshot. Formal F08 verification and PDF/Word export are not yet integrated.</p>
      </div>
    </main>}

    {stage === "applications" && <main className="aw-workspace aw-fade">
      <div className="aw-eyebrow">YOUR WORKSPACE</div>
      <h2>Applications</h2>
      <p className="aw-muted">Saved applications and historical reviewed resume versions.</p>
      <div className="aw-applications">
        {savedApplications.length ? savedApplications.map((item) => <article key={item.id} className="aw-application-card">
          <div><h3>{item.role_title}</h3><p>{item.company_name}</p></div>
          <div className="aw-application-meta"><span>{item.status}</span>
            <span>{versionCounts[item.id] ?? "—"} resume versions</span></div>
        </article>) : <p className="aw-muted">No saved applications yet. Create a resume to add your first application.</p>}
      </div>
      <button className="aw-primary" onClick={() => changeStage("paste")}>Start another application →</button>
    </main>}
  </div>;
}

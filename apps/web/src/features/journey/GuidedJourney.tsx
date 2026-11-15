import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import type { User } from "../auth/types";
import type { CandidateStatement } from "../tailoring/types";
import { SharingPage } from "../sharing";
import {
  addEvidence, estimateOverlap,
  generateCandidates, getApplications, getApprovedStatements, getEvidence, getVersionCounts,
  assessRequirements, finalizeResume, generateCoverLetter, readRequirements, saveBlob,
  saveReviewedResume, suggestJobContext,
  type CoverLetterDraft, type CoverLetterTone, type RequirementAssessment,
  type JourneyApplication, type JourneyEvidence,
} from "./api";
import "./journey.css";
import { ApplicationWorkspace } from "./ApplicationWorkspace";
import { StoryboardOnboarding, EMPTY_PROFILE, type Profile } from "./StoryboardOnboarding";
import { EvidenceManager } from "../evidence/EvidenceProfilePage";
import {
  VerificationPanel, listStatements, submitStatement, type VerifiedStatementView,
} from "../verification";
import { STATUS_LABEL } from "../verification/types";
import { decideStatement } from "../review";
import { StatementReviewPage } from "../review";
import { downloadResume, type ResumeExportFormat } from "../resume/api";
import { InterviewPrepPage, type ApprovedStatement } from "../interview";
import {
  INTERVIEW_PREP_AVAILABLE, INTERVIEW_PREP_UNAVAILABLE,
} from "../interview/availability";

interface Props { user: User; token: string; logout: () => void }
type Stage = "setup" | "preparing" | "ready" | "paste" | "analyzing" | "analysis" |
  "match" | "generating" | "resume" | "exporting" | "applications" | "sharing" | "evidence" |
  "verification" | "review" | "interview" | "cover-letter";
function localProfileKey(id: string) { return `applywise.journey.profile.${id}`; }
function readProfile(id: string): Profile | null {
  try {
    const raw = localStorage.getItem(localProfileKey(id));
    if (!raw) return null;
    const value = JSON.parse(raw) as Profile;
    return value && typeof value.career === "string" && value.career ? value : null;
  } catch { return null; }
}
// Only the profile used to survive a reload, so a refresh sent the user back
// to the empty job box and threw away the extracted requirements, the
// requirement match and the generated claims -- every one of which costs a
// live model call to rebuild. The draft below is the recoverable part of the
// journey. Approvals are deliberately NOT in it: an F09 approval is a server
// record bound to one verification revision, so letting the browser assert
// "approved" would survive an evidence change that should have invalidated
// it. Those are re-fetched from the server on restore.
type ResumableStage = "paste" | "analysis" | "match" | "resume";
const RESUMABLE: readonly ResumableStage[] = ["paste", "analysis", "match", "resume"];
interface JourneyDraft {
  stage: ResumableStage;
  job: string;
  role: string;
  company: string;
  requirements: string[];
  candidates: CandidateStatement[];
  verdicts: Record<string, VerifiedStatementView>;
  deniedIds: string[];
}
function localDraftKey(id: string) { return `applywise.journey.draft.${id}`; }
function readDraft(id: string): JourneyDraft | null {
  try {
    const raw = localStorage.getItem(localDraftKey(id));
    if (!raw) return null;
    const value = JSON.parse(raw) as JourneyDraft;
    if (!value || !RESUMABLE.includes(value.stage)) return null;
    if (!Array.isArray(value.candidates) || !Array.isArray(value.requirements)) return null;
    return value;
  } catch { return null; }
}

const delay = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

function Spinner({ title, description }: { title: string; description: string }) {
  return <main className="aw-center-state aw-fade" role="status">
    <div className="aw-spinner" aria-hidden="true" />
    <h2>{title}</h2><p>{description}</p>
  </main>;
}

export function GuidedJourney({ user, token, logout }: Props) {
  const stored = readProfile(user.id);
  const draft = stored ? readDraft(user.id) : null;
  const [profile, setProfile] = useState<Profile>(stored ?? EMPTY_PROFILE);
  const [stage, setStage] = useState<Stage>(stored ? (draft?.stage ?? "paste") : "setup");
  const [job, setJob] = useState(draft?.job ?? "");
  const [role, setRole] = useState(draft?.role ?? "");
  const [company, setCompany] = useState(draft?.company ?? "");
  const [requirements, setRequirements] = useState<string[]>(draft?.requirements ?? []);
  const [evidence, setEvidence] = useState<JourneyEvidence[]>([]);
  const [candidates, setCandidates] = useState<CandidateStatement[]>(draft?.candidates ?? []);
  const [approvedIds, setApprovedIds] = useState<string[]>([]);
  const [deniedIds, setDeniedIds] = useState<string[]>(draft?.deniedIds ?? []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [savedApplications, setSavedApplications] = useState<JourneyApplication[]>([]);
  const [versionCounts, setVersionCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [evidenceReturnStage, setEvidenceReturnStage] = useState<Stage>("paste");
  const [verifiedStatements, setVerifiedStatements] = useState<VerifiedStatementView[]>([]);
  const [reviewStatementId, setReviewStatementId] = useState<string | null>(null);
  const [approvedStatements, setApprovedStatements] = useState<ApprovedStatement[]>([]);
  // F07 proposes; F08 decides. Keyed by the candidate id so the document
  // keeps its order while decisions are made against F08's own records.
  const [verdicts, setVerdicts] = useState<Record<string, VerifiedStatementView>>(draft?.verdicts ?? {});
  const [reviewError, setReviewError] = useState("");
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [assessments, setAssessments] = useState<RequirementAssessment[]>([]);
  const [assessing, setAssessing] = useState(false);
  // The application and trusted version behind the PDF/Word downloads, kept
  // so a second download does not finalize a second time.
  const [coverLetter, setCoverLetter] = useState<CoverLetterDraft | null>(null);
  const [coverTone, setCoverTone] = useState<CoverLetterTone>("professional");
  const [coverBusy, setCoverBusy] = useState(false);
  const [finalApplicationId, setFinalApplicationId] = useState<string | null>(null);
  const [finalVersionId, setFinalVersionId] = useState<string | null>(null);

  // Keep the recoverable journey in step with the screen.
  useEffect(() => {
    if (!RESUMABLE.includes(stage as ResumableStage)) return;
    const resumable = stage as ResumableStage;
    try {
      localStorage.setItem(localDraftKey(user.id), JSON.stringify({
        stage: resumable, job, role, company, requirements, candidates, verdicts, deniedIds,
      } satisfies JourneyDraft));
    } catch { /* a full or disabled store must not break the journey */ }
  }, [user.id, stage, job, role, company, requirements, candidates, verdicts, deniedIds]);

  // A restored journey asks the server which claims are approved, because the
  // browser is not allowed to be the authority on that. It reloads the
  // evidence in the same pass: the export checks every claim's citations
  // against this list, so a journey restored without it fails that check on
  // evidence that is approved and present.
  useEffect(() => {
    if (!draft?.candidates.length) return;
    let live = true;
    void (async () => {
      try {
        const [approved, records] = await Promise.all([
          getApprovedStatements(token),
          getEvidence(token),
        ]);
        if (!live) return;
        setEvidence(records);
        const ids = new Set(approved.map((item) => item.statement_id));
        setApprovedIds(draft.candidates.filter((item) => ids.has(item.statement_id))
          .map((item) => item.statement_id));
      } catch { /* leave them unreviewed; the user can approve again */ }
    })();
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      const previous = readProfile(user.id);
      if (profile.experience.trim() && profile.experience.trim() !== previous?.experience.trim()) {
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
    // Fallback title: the first line, which is only right when the posting
    // happens to open with the role. "Acme is seeking a talented Senior
    // Engineer" becomes the whole sentence, which is why the model is asked.
    const first = lines[0]?.replace(/^job title:\s*/i, "").slice(0, 120) ?? "";
    const reqs = readRequirements(job);
    try {
      const [records, suggestion] = await Promise.all([
        getEvidence(token),
        // Best effort only: the fallback below is already usable, so a provider
        // failure must not stop the user reaching the next screen.
        suggestJobContext(token, job).catch(() => null),
        delay(850),
      ]);
      setEvidence(records);
      setRole((current) =>
        current || suggestion?.role_title || (first.length < 90 ? first : profile.career));
      if (suggestion?.company_name) {
        setCompany((current) => current || suggestion.company_name);
      }
      // readRequirements() takes the first ten long lines, so on a posting
      // without bullet characters it returns the metadata block and stops
      // before the duties. The model reads the whole posting, so prefer it and
      // keep the heuristic only for when it returns nothing.
      setRequirements(suggestion?.requirements?.length ? suggestion.requirements : reqs);
      setStage("analysis");
    } catch (err) {
      setStage("paste");
      setError(err instanceof Error ? err.message : "Could not load your evidence.");
    }
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
      setApprovedIds([]); setDeniedIds([]); setReviewError("");
      setVerdicts(await verifyCandidates(result.statements));
      await delay(500);
      setStage("resume");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume generation could not complete.");
      setStage("match");
    }
  }

  /** Submit each F07 candidate to F08 and keep the verdict it returns.
   *
   * A candidate is born `verification_status: "PENDING"`, so until this runs
   * nothing in the document has been checked against anything. F08 classifies
   * it server-side against the user's own approved evidence; the client never
   * decides what a claim is worth.
   */
  async function verifyCandidates(items: CandidateStatement[]) {
    const entries = await Promise.all(items.map(async (item) => {
      const verdict = await submitStatement(token, {
        text: item.text, evidence_ids: item.evidence_ids,
      });
      return [item.statement_id, verdict] as const;
    }));
    return Object.fromEntries(entries) as Record<string, VerifiedStatementView>;
  }

  /** Record an approval or rejection through F09, not in component state.
   *
   * `expected_revision` is what makes the decision trustworthy: F09 refuses it
   * if the claim or any cited evidence changed since this verdict was read, and
   * refuses approval of an UNSUPPORTED claim outright (409).
   */
  async function decide(candidateId: string, decision: "APPROVED" | "REJECTED") {
    const verdict = verdicts[candidateId];
    if (!verdict || busy) return;
    setBusy(true); setReviewError("");
    try {
      await decideStatement(token, verdict.statement_id, decision, verdict.revision);
      if (decision === "APPROVED") setApprovedIds((current) => [...current, candidateId]);
      else setDeniedIds((current) => [...current, candidateId]);
      setSelectedId(null);
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Could not record your decision.");
    } finally { setBusy(false); }
  }

  // F08, F09 and F15 each shipped a finished page that nothing imported, so
  // none of them had a click path and the STD cases covering them could not be
  // executed. These openers load what each page needs; the pages are unchanged.
  async function openVerification() {
    // `evidence` starts empty and is otherwise only filled by analyzeJob(), so
    // a user who signs in and opens this first saw no citable evidence even
    // with approved F02 records, and the panel's Add button stayed disabled.
    setError(""); setLoadingEvidence(true); setStage("verification");
    try {
      setEvidence(await getEvidence(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your approved evidence.");
    } finally { setLoadingEvidence(false); }
  }

  async function openReview() {
    setError(""); setStage("review"); setReviewStatementId(null);
    try {
      setVerifiedStatements(await listStatements(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your claims.");
    }
  }

  /** F11 drafts from approved statements, not from raw evidence.
   *
   * Each paragraph is a CANDIDATE: new prose that has not been through F08 or
   * F09, so it is never export-eligible and is labelled as a draft on screen.
   */
  async function openCoverLetter() {
    setError("");
    changeStage("cover-letter");
    if (coverLetter || coverBusy) return;
    await draftCoverLetter();
  }

  async function draftCoverLetter() {
    const approvedStatements = candidates
      .filter((item) => approvedIds.includes(item.statement_id))
      .map((item) => {
        const verdict = verdicts[item.statement_id];
        if (!verdict || verdict.status === "UNSUPPORTED") return null;
        return {
          statement_id: verdict.statement_id,
          text: verdict.text,
          evidence_ids: verdict.evidence_ids,
          verification_status: verdict.status,
        };
      })
      .filter((item): item is NonNullable<typeof item> => item !== null);
    if (!approvedStatements.length) {
      setError("Approve at least one claim before drafting a cover letter.");
      return;
    }
    setCoverBusy(true); setError("");
    try {
      setCoverLetter(await generateCoverLetter(token, {
        job_context: {
          job_title: role || profile.career || "Target position",
          company: company || null,
          description: job || "No description supplied.",
          requirements: requirements.slice(0, 20),
        },
        approved_statements: approvedStatements,
        tone: coverTone,
        max_paragraphs: 3,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not draft a cover letter.");
    } finally { setCoverBusy(false); }
  }

  async function openInterview() {
    setError("");
    if (!INTERVIEW_PREP_AVAILABLE) {
      // Never call a route the server does not serve; say why instead.
      setError(INTERVIEW_PREP_UNAVAILABLE);
      return;
    }
    setStage("interview");
    try {
      // Server-authoritative: F09 decides what counts as approved, not the client.
      setApprovedStatements(await getApprovedStatements(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load approved statements.");
    }
  }

  /** Enter the match screen, asking the provider how well the evidence answers.
   *
   * Best effort: on failure the screen falls back to the browser word count it
   * used before, and says which of the two it is showing.
   */
  async function openMatch() {
    setError(""); changeStage("match");
    const ids = evidence.filter((item) => item.status === "approved").map((item) => item.id);
    if (!requirements.length || !ids.length) { setAssessments([]); return; }
    setAssessing(true);
    try {
      const result = await assessRequirements(token, requirements, ids);
      // A body without the list is treated as no answer, not as zero coverage:
      // showing 0% because a response was malformed would be a lie.
      setAssessments(Array.isArray(result?.assessments) ? result.assessments : []);
    } catch {
      setAssessments([]);
    } finally { setAssessing(false); }
  }

  /** Download the approved statements as a real document.
   *
   * Saving to Applications stores a historical draft, which F10 refuses to
   * render by design. This takes the other road: F13 materialises a trusted version from
   * the F09-approved statements and F10 renders that. The server re-checks
   * every approval and its evidence first, so a claim approved against
   * evidence that has since changed stops here rather than reaching a PDF.
   */
  async function downloadFinal(format: ResumeExportFormat) {
    const approved = candidates.filter((item) => approvedIds.includes(item.statement_id));
    const statementIds = approved
      .map((item) => verdicts[item.statement_id]?.statement_id)
      .filter((value): value is string => Boolean(value));
    if (!statementIds.length || busy) return;
    setBusy(true); setError("");
    try {
      // Whatever route reached this screen, cite-checking needs the current
      // evidence, so load it when the journey does not already hold it.
      let records = evidence;
      if (!records.length) {
        records = await getEvidence(token);
        setEvidence(records);
      }
      let applicationId = finalApplicationId;
      if (!applicationId) {
        const application = await saveReviewedResume(
          token, { role, company, description: job }, records, approved);
        applicationId = application.id;
        setFinalApplicationId(applicationId);
      }
      let versionId = finalVersionId;
      if (!versionId) {
        versionId = (await finalizeResume(token, applicationId, statementIds)).id;
        setFinalVersionId(versionId);
      }
      const safeName = (user.full_name.trim() || "resume").replace(/[^a-z0-9_-]+/gi, "-");
      saveBlob(await downloadResume(token, versionId, format, "standard"),
        `${safeName}-resume.${format}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not prepare the document.");
    } finally { setBusy(false); }
  }

  /** Approve every claim F08 verified, in one action.
   *
   * Approval is still a decision the person makes and is still recorded
   * against each claim's exact verification revision -- this only spares them
   * clicking through claims they have no reason to question. INFERRED claims
   * are left alone deliberately: grounded is not certified, and whether to
   * stand behind one is exactly the judgement that should not be batched.
   */
  async function approveAllVerified() {
    const ready = activeCandidates.filter((item) =>
      !approvedIds.includes(item.statement_id)
      && verdicts[item.statement_id]?.status === "VERIFIED");
    for (const item of ready) {
      await decide(item.statement_id, "APPROVED");
    }
  }

  function newJob() {
    try { localStorage.removeItem(localDraftKey(user.id)); } catch { /* ignore */ }
    setJob(""); setRole(""); setCompany("");
    setRequirements([]); setCandidates([]); setApprovedIds([]); setDeniedIds([]);
    setAssessments([]);
    setFinalApplicationId(null); setFinalVersionId(null);
    changeStage("paste");
  }

  function openEvidence() {
    setEvidenceReturnStage(stage === "evidence" ? evidenceReturnStage : stage);
    changeStage("evidence");
  }

  async function closeEvidence() {
    try {
      // Re-read F02 before returning so approvals removed in the evidence
      // editor cannot remain in the match and generation screens.
      setEvidence(await getEvidence(token));
      changeStage(evidenceReturnStage);
    } catch (err) {
      // The user must be able to leave even if refreshing fails.
      changeStage(evidenceReturnStage);
      setError(err instanceof Error ? err.message : "Could not refresh approved evidence.");
    }
  }

  async function openApplications() {
    setError(""); setStage("applications");
    try {
      const [apps, counts] = await Promise.all([
        getApplications(token),
        getVersionCounts(token),
      ]);
      setSavedApplications(apps.slice().reverse());
      setVersionCounts(counts);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load applications."); }
  }

  function onApplicationChanged(updated: JourneyApplication) {
    setSavedApplications(current => current.map(item => item.id === updated.id ? updated : item));
  }

  async function exportReviewed() {
    const approved = candidates.filter((item) => approvedIds.includes(item.statement_id));
    if (!approved.length || candidates.some((item) => !approvedIds.includes(item.statement_id) && !deniedIds.includes(item.statement_id))) return;
    setBusy(true); setError("");
    try {
      await saveReviewedResume(token, { role, company, description: job }, evidence, approved);
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
  const LABEL = { COVERED: "Covered", PARTIAL: "Partly covered", MISSING: "Not evidenced" } as const;
  const TONE = { COVERED: "aw-approved", PARTIAL: "aw-partial", MISSING: "aw-missing" } as const;
  // The assessed view when the provider answered, the old word count when it
  // did not. The screen says which, because the two mean very different things.
  const coverage = assessments.length
    ? {
        assessed: true,
        percentage: Math.round(
          100 * assessments.filter((item) => item.coverage === "COVERED").length / assessments.length),
        covered: assessments.filter((item) => item.coverage === "COVERED").length,
        partial: assessments.filter((item) => item.coverage === "PARTIAL").length,
        missing: assessments.filter((item) => item.coverage === "MISSING").length,
        rows: assessments.map((item) => ({
          text: item.requirement,
          detail: item.note || "No note supplied.",
          label: LABEL[item.coverage],
          tone: TONE[item.coverage],
        })),
      }
    : {
        assessed: false,
        percentage: match.percentage,
        covered: match.matched.filter((item) => item.matches.length).length,
        partial: 0,
        missing: match.matched.filter((item) => !item.matches.length).length,
        rows: match.matched.map((item) => ({
          text: item.text,
          detail: item.matches.length
            ? item.matches.join(", ")
            : "No matching keywords in approved evidence",
          label: item.matches.length ? "Keyword match" : "Not found",
          tone: item.matches.length ? "aw-approved" : "aw-missing",
        })),
      };
  const initials = user.full_name.trim().split(/\s+/).slice(0, 2).map((x) => x[0]?.toUpperCase()).join("") || "?";

  return <div className="aw-journey">
    <header className="aw-topbar">
      <button className="aw-logo" type="button" onClick={() => changeStage("paste")}>ApplyWise</button>
      <nav className="aw-toplinks" aria-label="Your workspace">
        <button type="button" onClick={newJob}>New job</button>
        <button type="button" onClick={openEvidence}>Evidence</button>
        <button type="button" onClick={() => void openApplications()}>Applications</button>
        <button type="button" onClick={() => void openVerification()}>Verify claims</button>
        <button type="button" onClick={() => void openReview()}>Review claims</button>
        <button type="button" onClick={() => void openCoverLetter()}>Cover letter</button>
        {INTERVIEW_PREP_AVAILABLE &&
          <button type="button" onClick={() => void openInterview()}>Interview prep</button>}
        <button type="button" onClick={() => changeStage("sharing")}>Peer review</button>
        <div className="aw-avatar" title={user.full_name}>{initials}</div>
        <details className="aw-account"><summary>Profile</summary>
          <div className="aw-account-popup"><strong>{user.full_name}</strong><span>{user.email}</span>
            <button type="button" onClick={() => changeStage("setup")}>Edit profile</button></div>
        </details>
        <button type="button" onClick={logout}>Log out</button>
      </nav>
    </header>

    {error && <div className="aw-error" role="alert">{error}</div>}

    {stage === "verification" && (loadingEvidence
      ? <Spinner title="Loading your approved evidence"
          description="Reading the records you have approved, so a claim can cite them." />
      : <main className="aw-f08-workspace aw-fade" aria-label="Claim verification workspace">
        <VerificationPanel token={token} evidenceIds={approvedEvidence.map((item) => item.id)}
          onBack={() => changeStage("paste")} />
      </main>)}
    {stage === "cover-letter" && <main className="aw-f11-workspace aw-fade" aria-label="Cover letter workspace">
      <div className="aw-evidence-header">
        <button type="button" className="aw-link" onClick={() => changeStage("resume")}>← Back to resume</button>
      </div>
      <div className="aw-eyebrow">COVER LETTER</div>
      <h2>{company ? `Draft for ${company}` : "Cover letter draft"}</h2>
      <p className="aw-muted">Written from the claims you approved, so every paragraph
        traces back to your own evidence. This is a draft: unlike your resume it has
        not been through verification or approval, so it is not exported.</p>
      <div className="aw-cover-controls">
        <label>Tone
          <select value={coverTone} disabled={coverBusy}
            onChange={(event) => setCoverTone(event.target.value as CoverLetterTone)}>
            <option value="professional">Professional</option>
            <option value="warm">Warm</option>
            <option value="direct">Direct</option>
          </select>
        </label>
        <button type="button" className="aw-primary" disabled={coverBusy}
          onClick={() => void draftCoverLetter()}>
          {coverBusy ? "Drafting…" : coverLetter ? "Draft again" : "Draft cover letter"}
        </button>
        {coverLetter && <button type="button" className="aw-link" disabled={coverBusy}
          onClick={() => void navigator.clipboard?.writeText(
            coverLetter.paragraphs.map((item) => item.text).join("\n\n"))}>Copy text</button>}
      </div>
      {coverBusy && <p role="status" className="aw-muted">Drafting from your approved claims…</p>}
      {coverLetter && <article className="aw-cover-letter">
        {coverLetter.paragraphs.map((paragraph) => <p key={paragraph.paragraph_id}>{paragraph.text}</p>)}
        <footer className="aw-muted">
          Drafted by {coverLetter.provider} from {coverLetter.paragraphs.length}
          {coverLetter.paragraphs.length === 1 ? " paragraph" : " paragraphs"} ·
          every paragraph cites claims you approved.
        </footer>
      </article>}
      {coverLetter && coverLetter.rejected.length > 0 && <section className="aw-panel">
        <h3>{coverLetter.rejected.length} paragraph(s) discarded</h3>
        <p className="aw-muted">These failed F11's grounding checks and were not shown.</p>
        {coverLetter.rejected.map((item, index) => <p key={index} className="aw-muted">
          <strong>{item.reason}</strong> — {item.text.slice(0, 160)}
        </p>)}
      </section>}
    </main>}

    {stage === "review" && <main className="aw-f09-workspace aw-fade" aria-label="Statement review workspace">
      <div className="aw-evidence-header">
        <button type="button" className="aw-link" onClick={() => changeStage("paste")}>← Back to application</button>
      </div>
      {reviewStatementId
        ? <>
            <button type="button" className="aw-link" onClick={() => setReviewStatementId(null)}>← All claims</button>
            <StatementReviewPage token={token} statementId={reviewStatementId} />
          </>
        : <ul className="aw-review-list">
            {verifiedStatements.map((item) => <li key={item.statement_id}>
              <button type="button" onClick={() => setReviewStatementId(item.statement_id)}>
                <span>{item.text}</span><em>{item.status}</em>
              </button>
            </li>)}
            {!verifiedStatements.length && <li className="aw-review-empty">No claims submitted yet. Add one under Verify claims.</li>}
          </ul>}
    </main>}
    {stage === "interview" && <main className="aw-f15-workspace aw-fade" aria-label="Interview preparation workspace">
      <InterviewPrepPage token={token} statements={approvedStatements}
        onBack={() => changeStage("paste")} />
    </main>}
    {stage === "sharing" && <main className="aw-f14-workspace aw-fade" aria-label="Peer review sharing workspace">
      <SharingPage />
    </main>}
    {stage === "evidence" && <main className="aw-evidence-workspace aw-fade">
      <div className="aw-evidence-header">
        <button type="button" className="aw-link" onClick={() => void closeEvidence()}>← Back to application</button>
      </div>
      <EvidenceManager token={token} />
    </main>}
    {stage === "setup" && <StoryboardOnboarding profile={profile} setProfile={setProfile} finish={() => void finishSetup()} busy={busy} />}
    {stage === "preparing" && <main className="aw-center-state aw-fade aw-processing" role="status">
      <div className="aw-spinner" aria-hidden="true" />
      <h2>Setting up your workspace...</h2><p>Turning your experience into an evidence-based profile.</p>
      <div className="aw-process-steps"><span>✓ Saving your answers</span><span>✓ Recording your experience</span><span>◌ Preparing your profile</span></div>
    </main>}
    {stage === "ready" && <main className="aw-center-state aw-fade" role="status">
      <div className="aw-done-circle" aria-hidden="true">✓</div>
      <h2>All set!</h2><p>Your profile is ready. Let’s find your next opportunity.</p><button type="button" className="aw-primary" onClick={() => changeStage("paste")}>Continue →</button>
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

    {stage === "analysis" && <main className="aw-workspace aw-fade aw-storyboard-workspace">
      <div className="aw-flow-steps" aria-label="Application progress">
        <span className="is-active"><b>1</b> Analyze job</span><i />
        <span><b>2</b> Match evidence</span><i />
        <span><b>3</b> Tailor &amp; verify</span>
      </div>
      <div className="aw-center-heading"><div className="aw-eyebrow">JOB DESCRIPTION ANALYSIS</div>
        <h2>Here's what the role requires.</h2>
        <p className="aw-muted">Details identified from your posting. Please review them before continuing.</p></div>
      <div className="aw-analysis-grid aw-analysis-only">
        <section className="aw-panel">
          <h3>Position overview</h3>
          <label className="aw-overview-row">Job title<input value={role} onChange={e => setRole(e.target.value)} maxLength={200} aria-label="Job title" /></label>
          <label className="aw-overview-row">Company<input value={company} onChange={e => setCompany(e.target.value)} maxLength={200} placeholder="Not specified" aria-label="Company name" /></label>
          <div className="aw-overview-row"><span>Posting length</span><strong>{job.trim().length.toLocaleString()} characters</strong></div>
          <div className="aw-overview-row"><span>Requirements found</span><strong>{requirements.length}</strong></div>
          <p className="aw-card-footnote">Job details are derived from your own text, not an external verified posting.</p>
        </section>
        <section className="aw-panel">
          <h3>Top requirements</h3>
          {requirements.length ? requirements.slice(0, 8).map((value, i) =>
            <div className="aw-skill-requirement" key={i} style={{animationDelay:(i * 75)+"ms"}}>
              <span>{value}</span><small>Identified</small>
            </div>) : <p className="aw-muted">No distinct bullet requirements were detected. You can still continue with the full description.</p>}
        </section>
      </div>
      <div className="aw-summary-bar">
        <div className="aw-chips"><span className="aw-chip is-blue">{requirements.length} extracted requirements</span>
          <span className="aw-chip is-green">Your posting</span><span className="aw-chip">Review before tailoring</span></div>
        <button type="button" className="aw-primary" onClick={() => void openMatch()}>Match with my profile →</button>
      </div>
    </main>}

    {stage === "match" && <main className="aw-workspace aw-fade aw-storyboard-workspace">
      <div className="aw-flow-steps" aria-label="Application progress">
        <button type="button" onClick={() => changeStage("analysis")}><b>✓</b> Analyze job</button><i />
        <span className="is-active"><b>2</b> Match evidence</span><i />
        <span><b>3</b> Tailor &amp; verify</span>
      </div>
      <div className="aw-center-heading"><div className="aw-eyebrow">YOUR EVIDENCE MATCH</div>
        <h2>You're making a grounded match.</h2>
        <p className="aw-muted">{coverage.assessed
          ? "Each requirement is assessed against the evidence you approved."
          : "Each match is based on words found in approved career evidence."}</p></div>
      <div className="aw-match-layout">
        <section className="aw-panel aw-match-overview">
          <h3>Overall match</h3>
          <div className="aw-match-circle" style={{"--percent": coverage.percentage + "%"} as CSSProperties}>
            <strong>{coverage.percentage}%</strong></div>
          <p className="aw-estimate-note">{coverage.assessed
            ? "Assessed against the evidence you approved. Advisory only: it shows what you can currently evidence, not whether anything you write is supported. That check is separate and does not use a language model."
            : "Keyword overlap between these requirements and your approved evidence, counted in your browser. This is not verification: nothing here says whether any claim is supported by your evidence."}</p>
          <p className="aw-center aw-muted">{assessing
            ? "Assessing your evidence…"
            : coverage.assessed ? "Requirements your evidence covers" : "Estimated keyword overlap"}</p>
          <div className="aw-match-key">
            <span><i className="is-found"/> {coverage.assessed ? "Covered" : "Requirements with overlap"} <strong>{coverage.covered}</strong></span>
            {coverage.assessed && <span><i className="is-partial"/> Partly covered <strong>{coverage.partial}</strong></span>}
            <span><i className="is-missing"/> {coverage.assessed ? "Not evidenced" : "No keyword overlap"} <strong>{coverage.missing}</strong></span>
          </div>
          <p className="aw-card-footnote">This is not a validated ATS or hiring-success score.</p>
        </section>
        <section className="aw-panel aw-match-evidence">
          <h3>Evidence from your career profile</h3>
          <p className="aw-muted">Requirements are compared only to your approved evidence.</p>
          {coverage.rows.length ? coverage.rows.map((item,i) =>
            <div className="aw-match-requirement" key={i} style={{animationDelay:(i * 75)+"ms"}}>
              <div><strong>{item.text}</strong><small>{item.detail}</small></div>
              <span className={item.tone}>{item.label}</span>
            </div>) : <p className="aw-muted">No separate requirements were detected in this posting.</p>}
        </section>
      </div>
      <section className="aw-panel aw-evidence-review">
        <div className="aw-panel-heading"><h3>Your career evidence</h3><span>{approvedEvidence.length} approved</span></div>
        <p className="aw-muted">Manage projects and experience in one evidence workspace. Only evidence you've approved can support generated statements.</p>
        {evidence.length ? <div className="aw-evidence-list">{evidence.map(item =>
          <article className="aw-evidence-row" key={item.id}>
            <div><strong>{item.title}</strong><small>{item.description || item.role || "Evidence item"}</small></div>
            <span className={item.status === "approved" ? "aw-approved" : "aw-missing"}>
              {item.status === "approved" ? "✓ Approved" : "Needs approval"}
            </span>
          </article>)}</div> : <p className="aw-muted">No evidence saved yet. Add an example of your own work in the Evidence workspace.</p>}
        <button type="button" className="aw-link" onClick={openEvidence}>Open evidence workspace →</button>
      </section>
      <div className="aw-summary-bar">
        <p className="aw-muted">Every generated claim must be supported by evidence you approved.</p>
        <button type="button" className="aw-primary" disabled={!approvedEvidence.length}
          onClick={() => void generateResume()}>Generate resume →</button>
      </div>
    </main>}
    {stage === "generating" && <main className="aw-resume-generating aw-fade" role="status">
      <div className="aw-center-heading">
        <div className="aw-eyebrow">TAILORED RESUME CREATION</div>
        <h2>Building your resume...</h2>
        <p className="aw-muted">Grounding statements in the evidence you approved.</p>
      </div>
      <div className="aw-generating-layout">
        <div className="aw-generating-paper" aria-hidden="true">
          <h3>{user.full_name}</h3><p>{role}</p><hr />
          <div className="aw-gen-heading">PROFESSIONAL SUMMARY</div>
          <i/><i/><i className="short"/><div className="aw-gen-heading">EXPERIENCE</div>
          <i/><i/><i/><i className="short"/>
          <div className="aw-gen-heading">SKILLS</div><i/><i className="short"/>
        </div>
        <aside className="aw-panel aw-generating-checklist">
          <div className="aw-gen-icon">✧</div><h3>Writing with evidence</h3>
          <p className="aw-muted">Every statement is drafted using your approved career information.</p>
          <ul><li>✓ Reading job requirements</li><li>✓ Selecting relevant experience</li>
            <li>◌ Building resume structure</li><li>◌ Writing candidate statements</li></ul>
          <div className="aw-gen-progress"><span /></div>
          <small>Preparing your review</small>
        </aside>
      </div>
    </main>}

    {(stage === "resume" || stage === "exporting") && <main className={`aw-resume-stage aw-fade aw-storyboard-resume ${stage === "exporting" ? "aw-exporting" : ""}`}>
      <div className="aw-storyboard-resume-head">
        <div><div className="aw-eyebrow">REVIEW &amp; APPROVAL</div>
          <h2>{pendingCount ? "Review claims before exporting" : "Ready when you are."}</h2></div>
        <div className="aw-review-head-actions">
          {activeCandidates.some((item) => !approvedIds.includes(item.statement_id)
            && verdicts[item.statement_id]?.status === "VERIFIED") &&
            <button type="button" className="aw-link" disabled={busy}
              onClick={() => void approveAllVerified()}>Approve all verified</button>}
          <span className={pendingCount ? "aw-review-count" : "aw-review-count is-done"}>
            {pendingCount ? pendingCount + " claims need attention" : "All statements reviewed"}
          </span>
        </div>
      </div>
      <div className="aw-resume-layout">
        <article className={`aw-document ${selectedId ? "aw-document-dim" : ""}`}>
          <header><h3>{user.full_name}</h3><strong>{role || profile.career}</strong>
            <p>{user.email}{company ? "  ·  " + company : ""}</p></header>
          <h4>Professional summary</h4>
          <p className="aw-resume-summary">Career focus: {profile.career}. The experience below is selected from approved evidence for this role.</p>
          <h4>Relevant experience</h4>
          {activeCandidates.map((item, index) => {
            const approved = approvedIds.includes(item.statement_id);
            const selected = selectedId === item.statement_id;
            const citations = evidence.filter(record => item.evidence_ids.includes(record.id));
            return <div key={item.statement_id}
              className={`aw-document-line ${approved ? "is-approved" : "needs-review"} ${selected ? "is-selected" : ""}`}
              style={{ animationDelay: (index * 145) + "ms" }}>
              {approved ? <p className="aw-approved-line">✓ {item.text}</p> :
                <button type="button" className="aw-line-preview" aria-expanded={selected}
                  onClick={() => setSelectedId(selected ? null : item.statement_id)}>
                  <span>• {item.text}</span><small>{selected ? "Hide evidence ↑" : "Needs approval · Review ↗"}</small>
                </button>}
              {selected && !approved && <div className="aw-line-detail">
                <div className="aw-line-detail-title"><strong>Evidence review · Experience claim</strong><span>Needs approval</span></div>
                <p className="aw-claim-text">{item.text}</p>
                <div className="aw-source-evidence"><strong>Your source evidence</strong>
                  {citations.map(ev => <p key={ev.id}><b>{ev.title}:</b> {ev.description || ev.role || ev.title}</p>)}
                </div>
                {verdicts[item.statement_id] && <div
                  className={`aw-verdict is-${verdicts[item.statement_id].status.toLowerCase()}`}>
                  <strong>{STATUS_LABEL[verdicts[item.statement_id].status]}</strong>
                  <ul>{verdicts[item.statement_id].findings.map((finding, position) =>
                    <li key={position}>{finding.detail}</li>)}</ul>
                </div>}
                <p className="aw-review-note">{verdicts[item.statement_id]?.status === "UNSUPPORTED"
                  ? "This claim states something your approved evidence does not contain, so it cannot be approved or exported."
                  : "Checked against your approved evidence. Approving records your decision against this exact version."}</p>
                {reviewError && <p className="aw-review-error" role="alert">{reviewError}</p>}
                <div className="aw-review-actions">
                  <button type="button" disabled={busy}
                    onClick={() => void decide(item.statement_id, "REJECTED")}>Deny claim</button>
                  <button type="button"
                    disabled={busy || verdicts[item.statement_id]?.status === "UNSUPPORTED"}
                    onClick={() => void decide(item.statement_id, "APPROVED")}>Approve claim ✓</button>
                </div>
              </div>}
            </div>;
          })}
          {!activeCandidates.length && <p className="aw-muted">All candidate statements have been denied. Go back to matching to generate a different draft.</p>}
          {profile.focus.length > 0 && <><h4>Technical skills</h4>
            <p className="aw-skill-line">{profile.focus.join(" · ")}</p></>}
        </article>
        <aside className="aw-resume-sidebar">
          <section className="aw-panel">
            {pendingCount ? <>
              <h3>Verification queue</h3>
              <p className="aw-muted">Select any highlighted statement to inspect its supporting evidence.</p>
              {activeCandidates.filter(item => !approvedIds.includes(item.statement_id)).map((item,index) =>
                <button className="aw-queue-item" type="button" key={item.statement_id}
                  onClick={() => setSelectedId(item.statement_id)}>
                  <strong>Statement {index+1}</strong><small>{item.text}</small><span>● Needs approval</span>
                </button>)}
              <div className="aw-queue-note">◇ Unsupported claims must be denied, never exported.</div>
            </> : <>
              <div className="aw-done-circle aw-review-complete" aria-hidden="true">✓</div>
              <h3>Review complete</h3>
              <p className="aw-muted">Every remaining candidate was checked against your approved evidence and approved by you.</p>
            </>}
          </section>
          {deniedIds.length > 0 && <div className="aw-reflow-message" role="status">
            ✓ {deniedIds.length} {deniedIds.length === 1 ? "claim removed" : "claims removed"} · Document layout adjusted
          </div>}
          <button className="aw-link aw-back-review" type="button" onClick={() => changeStage("match")}>← Back to evidence</button>
          <button type="button" className="aw-primary aw-export-button"
            disabled={busy || pendingCount !== 0 || approvedIds.length === 0}
            onClick={() => void exportReviewed()}>Save to My Applications →</button>
          <div className="aw-final-downloads">
            <button type="button" disabled={busy || !approvedIds.length}
              onClick={() => void downloadFinal("pdf")}>Download PDF</button>
            <button type="button" disabled={busy || !approvedIds.length}
              onClick={() => void downloadFinal("docx")}>Download Word</button>
          </div>
          <p className="aw-export-hint">PDF and Word are rendered from a finalized version: the server
            re-checks every approval and its evidence before writing the file. Saving to My
            Applications keeps a historical draft for your records, which is deliberately not
            exportable on its own.</p>
        </aside>
      </div>
      {stage === "exporting" && <div className="aw-export-toast" role="status">✓ Resume saved to your Applications</div>}
    </main>}

    {stage === "applications" && <ApplicationWorkspace
      token={token}
      fullName={user.full_name}
      applications={savedApplications}
      versionCounts={versionCounts}
      onChange={onApplicationChanged}
      onNewJob={newJob}
      onEditProfile={() => changeStage("setup")}
    />}
  </div>;
}

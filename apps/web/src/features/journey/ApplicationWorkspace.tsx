import { useState, type FormEvent } from "react";
import { ResumeVersionHistory } from "./ResumeVersionHistory";
import { ResumePage } from "../resume/ResumePage";
import {
  ALLOWED_STATUS_CHANGES, APPLICATION_STATUSES,
  changeApplicationStatus, updateApplicationDetails,
  type JourneyApplication, type JourneyApplicationStatus,
} from "./api";

interface Props {
  token: string;
  applications: JourneyApplication[];
  versionCounts: Record<string, number>;
  onChange: (application: JourneyApplication) => void;
  onNewJob: () => void;
  onEditProfile: () => void;
}

function isKnownStatus(value: string): value is JourneyApplicationStatus {
  return APPLICATION_STATUSES.some((status) => status === value);
}

function formatDate(value?: string | null): string {
  if (!value) return "Not set";
  const date = new Date(value + (value.includes("T") ? "" : "T12:00:00"));
  return Number.isNaN(date.getTime()) ? "Not set" : date.toLocaleDateString();
}

/** F13 application records are editable; historical resume versions remain immutable. */
export function ApplicationWorkspace({
  token, applications, versionCounts, onChange, onNewJob, onEditProfile,
}: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [historyOpenId, setHistoryOpenId] = useState<string | null>(null);
  const [exportOpenId, setExportOpenId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const update = (result: JourneyApplication) => {
    onChange(result);
    setError("");
    setNotice("Application updated.");
  };

  async function saveDetails(event: FormEvent<HTMLFormElement>, id: string) {
    event.preventDefault();
    if (savingId) return;
    const data = new FormData(event.currentTarget);
    const notes = String(data.get("notes") ?? "").trim();
    const jobUrl = String(data.get("job_url") ?? "").trim();
    const nextAction = String(data.get("next_action_on") ?? "");
    setSavingId(id);
    setError("");
    setNotice("");
    try {
      const result = await updateApplicationDetails(token, id, {
        notes: notes || null,
        job_url: jobUrl || null,
        next_action_on: nextAction || null,
      });
      update(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save application details.");
    } finally {
      setSavingId(null);
    }
  }

  async function changeStatus(id: string, status: JourneyApplicationStatus) {
    if (savingId) return;
    setSavingId(id);
    setError("");
    setNotice("");
    try {
      update(await changeApplicationStatus(token, id, status));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not change application status.");
    } finally {
      setSavingId(null);
    }
  }

  return <main className="aw-app-workspace aw-fade">
    <aside className="aw-app-sidebar">
      <strong>Workspace</strong>
      <button type="button" onClick={onNewJob}>▦ Dashboard</button>
      <span className="is-selected">▢ My Applications</span>
      <button type="button" onClick={onEditProfile}>♙ My Profile</button>
      <button type="button" onClick={onNewJob}>＋ New job</button>
    </aside>
    <div className="aw-app-content">
      <div className="aw-app-header">
        <div>
          <div className="aw-eyebrow">YOUR APPLICATION WORKSPACE</div>
          <h2>My Applications</h2>
          <p className="aw-muted">Manage job progress, follow-up dates, notes, and saved resume versions.</p>
        </div>
        <button className="aw-primary" type="button" onClick={onNewJob}>New application →</button>
      </div>
      <div className="aw-app-stats">
        <div><span>Total applications</span><strong>{applications.length}</strong></div>
        <div><span>Drafts</span><strong>{applications.filter(item => item.status === "draft").length}</strong></div>
        <div><span>Saved resume versions</span><strong>{Object.values(versionCounts).reduce((a,b) => a+b, 0)}</strong></div>
      </div>
      {error && <p role="alert" className="aw-error">{error}</p>}
      {notice && <p role="status" className="aw-app-notice">{notice}</p>}
      <section className="aw-app-list" aria-label="Saved applications">
        {applications.length ? applications.map(item => {
          const expanded = expandedId === item.id;
          const statusOptions: readonly JourneyApplicationStatus[] = isKnownStatus(item.status)
            ? ALLOWED_STATUS_CHANGES[item.status as JourneyApplicationStatus] : [];
          return <article key={item.id} className="aw-app-entry">
            <div className="aw-app-list-row">
              <div className="aw-app-doc-icon" aria-hidden="true">▤</div>
              <div><h3>{item.role_title}</h3><p>{item.company_name}</p></div>
              <span className="aw-app-status">{item.status}</span>
              <span className="aw-app-version-count">{versionCounts[item.id] ?? 0} resume {versionCounts[item.id] === 1 ? "version" : "versions"}</span>
              <button type="button" className="aw-app-expand" aria-expanded={expanded}
                onClick={() => { setExpandedId(expanded ? null : item.id); setError(""); setNotice(""); }}>
                {expanded ? "Close" : "Manage"}
              </button>
            </div>
            {expanded && <div className="aw-app-details">
              <div className="aw-app-detail-summary">
                <div><span>Created</span><strong>{formatDate(item.created_at)}</strong></div>
                <div><span>Applied</span><strong>{formatDate(item.applied_on)}</strong></div>
                <div><span>Next action</span><strong>{formatDate(item.next_action_on)}</strong></div>
                <div><span>Resume versions</span><strong>{versionCounts[item.id] ?? 0}</strong></div>
              </div>
<div className="aw-history-action-row">
  <button
    type="button"
    aria-expanded={historyOpenId === item.id}
    className="aw-app-expand"
    onClick={() =>
      setHistoryOpenId(current =>
        current === item.id ? null : item.id
      )
    }
  >
    {historyOpenId === item.id
      ? "Hide resume history"
      : "View resume history"}
  </button>

  <button
    type="button"
    aria-expanded={exportOpenId === item.id}
    className="aw-app-expand"
    onClick={() =>
      setExportOpenId(current =>
        current === item.id ? null : item.id
      )
    }
  >
    {exportOpenId === item.id
      ? "Hide resume export"
      : "Export resume"}
  </button>
</div>
              {historyOpenId === item.id && <ResumeVersionHistory
                key={item.id} token={token} applicationId={item.id} />}
{exportOpenId === item.id && (
  <ResumePage
    key={item.id}
    token={token}
    applicationId={item.id}
  />
)}
        <div className="aw-app-detail-cols">
                <form key={item.id + ":" + (item.notes ?? "") + ":" + (item.job_url ?? "") + ":" + (item.next_action_on ?? "")}
                  onSubmit={event => void saveDetails(event, item.id)}>
                  <h4>Application details</h4>
                  <label>Job posting URL
                    <input type="url" name="job_url" placeholder="https://example.com/job"
                      defaultValue={item.job_url ?? ""} maxLength={1000} />
                  </label>
                  <label>Next action date
                    <input type="date" name="next_action_on" defaultValue={item.next_action_on ?? ""} />
                  </label>
                  <label>Notes
                    <textarea name="notes" rows={3} maxLength={5000}
                      placeholder="Interview preparation, contacts, or follow-up notes"
                      defaultValue={item.notes ?? ""} />
                  </label>
                  <button type="submit" className="aw-primary" disabled={!!savingId}>
                    {savingId === item.id ? "Saving..." : "Save details"}
                  </button>
                </form>
                <div className="aw-app-status-controls">
                  <h4>Application status</h4>
                  <p className="aw-muted">Current: <strong>{item.status}</strong></p>
                  {statusOptions.length ? <label>Move to
                    <select aria-label={`Change status for ${item.role_title}`} key={item.id + item.status}
                      defaultValue="" disabled={!!savingId}
                      onChange={event => {
                        const next = event.target.value;
                        if (isKnownStatus(next)) void changeStatus(item.id, next);
                      }}>
                      <option value="" disabled>Choose next status</option>
                      {statusOptions.map((status: JourneyApplicationStatus) => <option key={status} value={status}>{status}</option>)}
                    </select>
                  </label> :
                    <p className="aw-muted">This is a final status. Reopening is not supported by the application lifecycle.</p>}
                  <p className="aw-muted">Status changes are saved to your account. Resume versions are immutable history.</p>
                </div>
              </div>
            </div>}
          </article>;
        }) : <div className="aw-app-empty">
          <p>No saved applications yet.</p>
          <button type="button" className="aw-primary" onClick={onNewJob}>Start your first application →</button>
        </div>}
      </section>
      <p className="aw-app-disclosure">Edits update your saved application record. Historical resume snapshots are never changed by these controls.</p>
    </div>
  </main>;
}

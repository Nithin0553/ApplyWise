import { useEffect, useMemo, useState } from "react";

import { getVersions, type JourneyResumeVersion } from "./api";
import "./resume-history.css";

interface Props {
  token: string;
  applicationId: string;
}

type SavedStatement = JourneyResumeVersion["snapshot"]["statements"][number];

function readableDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown date" : date.toLocaleString();
}

function contentKey(statement: SavedStatement): string {
  // IDs often change when generating a new version. Compare the actual
  // immutable statement text, not only the newly generated statement UUID.
  return statement.text.trim().replace(/\s+/g, " ");
}

function SnapshotStatement({ statement, change }: {
  statement: SavedStatement;
  change?: "added" | "unchanged";
}) {
  return <li className="aw-history-statement">
    <div className="aw-history-statement-body">
      <p>{statement.text}</p>
      <div className="aw-history-statement-tags">
        {change === "added" && <span className="aw-history-tag is-added">Added in selected version</span>}
        {change === "unchanged" && <span className="aw-history-tag">Unchanged</span>}
        <span className="aw-history-tag">{statement.verification_status}</span>
        <span className="aw-history-tag">{statement.approval_status === "APPROVED" ? "User reviewed" : statement.approval_status}</span>
        <span className="aw-history-tag">{statement.origin ?? "DRAFT_USER_REVIEWED"}</span>
      </div>
      {statement.evidence_ids.length > 0 &&
        <small>{statement.evidence_ids.length} saved evidence {statement.evidence_ids.length === 1 ? "reference" : "references"}</small>}
    </div>
  </li>;
}

/**
 * Historical F13 snapshots are read-only and scoped to the signed-in owner by
 * the API. The snapshot's labels are historical data, not an F08 eligibility
 * decision; in particular a user-reviewed draft is not an exportable final.
 */
export function ResumeVersionHistory({ token, applicationId }: Props) {
  const [versions, setVersions] = useState<JourneyResumeVersion[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [comparisonId, setComparisonId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setVersions([]);
    setSelectedId("");
    setComparisonId("");
    void getVersions(token, applicationId).then(records => {
      if (!active) return;
      const ordered = records.slice().sort((a, b) => a.version_number - b.version_number);
      setVersions(ordered);
      setSelectedId(ordered.at(-1)?.id ?? "");
    }).catch(cause => {
      if (!active) return;
      setError(cause instanceof Error ? cause.message : "Could not load resume version history.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [token, applicationId, attempt]);

  const selected = useMemo(
    () => versions.find(version => version.id === selectedId),
    [versions, selectedId],
  );
  const comparison = useMemo(
    () => versions.find(version => version.id === comparisonId),
    [versions, comparisonId],
  );
  const previousTexts = new Set((comparison?.snapshot.statements ?? []).map(contentKey));
  const currentTexts = new Set((selected?.snapshot.statements ?? []).map(contentKey));
  const removed = comparison?.snapshot.statements.filter(item => !currentTexts.has(contentKey(item))) ?? [];

  return <section className="aw-history" aria-label="Resume version history">
    <div className="aw-history-header">
      <div>
        <h4>Saved resume versions</h4>
        <p>These snapshots are immutable records. Reviewing a draft does not constitute automatic verification.</p>
      </div>
    </div>

    {loading && <p role="status">Loading saved versions…</p>}
    {!loading && error && <div role="alert" className="aw-history-error">
      <p>{error}</p>
      <button type="button" onClick={() => setAttempt(previous => previous + 1)}>Retry loading versions</button>
    </div>}
    {!loading && !error && versions.length === 0 && <p className="aw-history-empty">
      No saved resume versions for this application yet.
    </p>}

    {!loading && !error && selected && <>
      <div className="aw-history-controls">
        <label>View version
          <select aria-label="View resume version" value={selectedId}
            onChange={event => {
              setSelectedId(event.target.value);
              if (event.target.value === comparisonId) setComparisonId("");
            }}>
            {versions.map(version =>
              <option value={version.id} key={version.id}>
                Version {version.version_number} — {readableDate(version.created_at)}
              </option>)}
          </select>
        </label>
        {versions.length > 1 && <label>Compare with
          <select aria-label="Compare with resume version" value={comparisonId}
            onChange={event => setComparisonId(event.target.value)}>
            <option value="">No comparison</option>
            {versions.filter(version => version.id !== selectedId).map(version =>
              <option value={version.id} key={version.id}>Version {version.version_number}</option>)}
          </select>
        </label>}
      </div>

      <div className="aw-history-snapshot" aria-live="polite">
        <div className="aw-history-snapshot-title">
          <strong>Resume version {selected.version_number}</strong>
          <span>{readableDate(selected.created_at)}</span>
        </div>
        <p className="aw-history-disclosure">Historical {selected.snapshot.statements.length} statement
          {selected.snapshot.statements.length === 1 ? "" : "s"} · These values are not an export approval.</p>

        {selected.snapshot.statements.length > 0 ? <ol className="aw-history-statements">
          {selected.snapshot.statements.map(statement =>
            <SnapshotStatement statement={statement} key={statement.statement_id}
              change={comparison ? (previousTexts.has(contentKey(statement)) ? "unchanged" : "added") : undefined}/>)}
        </ol> : <p>No statements were stored in this version.</p>}

        {comparison && <div className="aw-history-comparison">
          <h5>Changes compared with version {comparison.version_number}</h5>
          <p>{selected.snapshot.statements.filter(statement => !previousTexts.has(contentKey(statement))).length} added, {removed.length} removed, {" "}
            {selected.snapshot.statements.filter(statement => previousTexts.has(contentKey(statement))).length} unchanged.</p>
          {removed.length > 0 && <div className="aw-history-removed">
            <strong>Statements only in version {comparison.version_number}</strong>
            <ul>{removed.map(item => <li key={item.statement_id}>{item.text}</li>)}</ul>
          </div>}
          <small>Comparison uses exact statement wording after whitespace normalization; it does not assess semantic changes or claim accuracy.</small>
        </div>}
      </div>
    </>}
  </section>;
}

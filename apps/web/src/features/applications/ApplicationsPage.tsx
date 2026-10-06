import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth";
import { ApplicationForm } from "./ApplicationForm";
import { ApplicationTracker } from "./ApplicationTracker";
import {
  ApplicationsApiError,
  createApplication,
  getResumeVersion,
  listApplications,
  listResumeVersions,
  toApplicationFormValues,
  toApplicationSummary,
  toResumeVersionSummary,
  transitionApplicationStatus,
  updateApplication,
  type ApplicationApiRecord,
  type ResumeVersionApiRecord,
} from "./api";
import "./applications.css";
import type { ApplicationFormValues, ApplicationStatus } from "./types";

type EditorState =
  | { kind: "create" }
  | { kind: "edit"; applicationId: string }
  | null;

function errorMessage(error: unknown): string {
  if (error instanceof ApplicationsApiError) return error.message;
  return "Something went wrong while loading applications.";
}

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function ApplicationsPage() {
  const { token } = useAuth();
  const [records, setRecords] = useState<ApplicationApiRecord[]>([]);
  const [versionsByApplication, setVersionsByApplication] = useState<
    Record<string, ResumeVersionApiRecord[]>
  >({});
  const [selectedApplicationId, setSelectedApplicationId] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<ResumeVersionApiRecord | null>(null);
  const [editor, setEditor] = useState<EditorState>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) {
      setRecords([]);
      setVersionsByApplication({});
      setSelectedApplicationId(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const applications = await listApplications(token);
      const versionEntries = await Promise.all(
        applications.map(async (application) => [
          application.id,
          await listResumeVersions(token, application.id),
        ] as const),
      );
      const versionMap = Object.fromEntries(versionEntries);

      setRecords(applications);
      setVersionsByApplication(versionMap);
      setSelectedApplicationId((current) => {
        if (current && applications.some((application) => application.id === current)) {
          return current;
        }
        return applications[0]?.id ?? null;
      });
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedRecord = records.find(
    (record) => record.id === selectedApplicationId,
  );

  const applicationSummaries = useMemo(
    () =>
      records.map((record) =>
        toApplicationSummary(record, versionsByApplication[record.id]?.length ?? 0),
      ),
    [records, versionsByApplication],
  );

  const selectedResumeVersions = useMemo(
    () =>
      (selectedApplicationId ? versionsByApplication[selectedApplicationId] ?? [] : []).map(
        toResumeVersionSummary,
      ),
    [selectedApplicationId, versionsByApplication],
  );

  async function saveCreate(values: ApplicationFormValues) {
    if (!token) return;
    setIsSaving(true);
    setError(null);
    try {
      const created = await createApplication(token, values);
      setEditor(null);
      await load();
      setSelectedApplicationId(created.id);
    } catch (saveError) {
      setError(errorMessage(saveError));
    } finally {
      setIsSaving(false);
    }
  }

  async function saveEdit(applicationId: string, values: ApplicationFormValues) {
    if (!token) return;
    setIsSaving(true);
    setError(null);
    try {
      await updateApplication(token, applicationId, values);
      setEditor(null);
      await load();
      setSelectedApplicationId(applicationId);
    } catch (saveError) {
      setError(errorMessage(saveError));
    } finally {
      setIsSaving(false);
    }
  }

  async function changeStatus(applicationId: string, status: ApplicationStatus) {
    if (!token) return;
    setError(null);
    try {
      await transitionApplicationStatus(token, applicationId, status);
      await load();
      setSelectedApplicationId(applicationId);
    } catch (statusError) {
      setError(errorMessage(statusError));
    }
  }

  async function openVersion(resumeVersionId: string) {
    if (!token) return;
    setError(null);
    try {
      setSelectedVersion(await getResumeVersion(token, resumeVersionId));
    } catch (versionError) {
      setError(errorMessage(versionError));
    }
  }

  if (!token) {
    return <p>Sign in as a Job Seeker to manage applications.</p>;
  }

  return (
    <section className="applications-page" aria-label="Application tracking">
      {error ? (
        <div className="applications-page__error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => void load()}>
            Retry
          </button>
        </div>
      ) : null}

      {editor ? (
        <section className="applications-page__panel" aria-labelledby="application-editor-heading">
          <h2 id="application-editor-heading">
            {editor.kind === "create" ? "Add application" : "Edit application"}
          </h2>
          {editor.kind === "create" ? (
            <ApplicationForm
              submitLabel={isSaving ? "Saving…" : "Save application"}
              onSubmit={(values) => void saveCreate(values)}
              onCancel={() => setEditor(null)}
            />
          ) : selectedRecord && selectedRecord.id === editor.applicationId ? (
            <ApplicationForm
              initialValues={toApplicationFormValues(selectedRecord)}
              submitLabel={isSaving ? "Saving…" : "Update application"}
              onSubmit={(values) => void saveEdit(editor.applicationId, values)}
              onCancel={() => setEditor(null)}
            />
          ) : (
            <p>The application is no longer available.</p>
          )}
        </section>
      ) : null}

      {isLoading ? (
        <p className="applications-page__loading" role="status">
          Loading applications…
        </p>
      ) : (
        <ApplicationTracker
          applications={applicationSummaries}
          selectedApplicationId={selectedApplicationId}
          resumeVersions={selectedResumeVersions}
          onSelectApplication={(applicationId) => {
            setSelectedApplicationId(applicationId);
            setSelectedVersion(null);
            setEditor(null);
          }}
          onCreateApplication={() => {
            setEditor({ kind: "create" });
            setSelectedVersion(null);
          }}
          onEditApplication={(applicationId) => {
            setSelectedApplicationId(applicationId);
            setEditor({ kind: "edit", applicationId });
            setSelectedVersion(null);
          }}
          onStatusChange={(applicationId, status) => void changeStatus(applicationId, status)}
          onOpenVersion={(resumeVersionId) => void openVersion(resumeVersionId)}
        />
      )}

      {selectedVersion ? (
        <ResumeVersionDetails
          version={selectedVersion}
          onClose={() => setSelectedVersion(null)}
        />
      ) : null}
    </section>
  );
}

function ResumeVersionDetails({
  version,
  onClose,
}: {
  version: ResumeVersionApiRecord;
  onClose: () => void;
}) {
  return (
    <section className="applications-page__panel" aria-labelledby="resume-version-detail-heading">
      <div className="applications-page__panel-header">
        <div>
          <p className="application-tracker__eyebrow">Saved snapshot</p>
          <h2 id="resume-version-detail-heading">Resume version {version.version_number}</h2>
          <p>Saved {formatTimestamp(version.created_at)}</p>
        </div>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>

      <dl className="applications-page__snapshot-counts">
        <div>
          <dt>Evidence records</dt>
          <dd>{version.snapshot.evidence.length}</dd>
        </div>
        <div>
          <dt>Statements</dt>
          <dd>{version.snapshot.statements.length}</dd>
        </div>
      </dl>

      {version.snapshot.statements.length === 0 ? (
        <p>This version contains no statement snapshots.</p>
      ) : (
        <ol className="applications-page__statements">
          {version.snapshot.statements.map((statement) => (
            <li key={statement.statement_id}>
              <p>{statement.text}</p>
              <div className="applications-page__statement-meta">
                <span>{statement.verification_status}</span>
                <span>{statement.approval_status}</span>
                <span>
                  {statement.evidence_ids.length} evidence source
                  {statement.evidence_ids.length === 1 ? "" : "s"}
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

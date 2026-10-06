import "./applications.css";

import {
  APPLICATION_STATUS_LABELS,
  allowedApplicationStatuses,
  type ApplicationStatus,
  type ApplicationSummary,
  type ResumeVersionSummary,
} from "./types";

interface ApplicationTrackerProps {
  applications: readonly ApplicationSummary[];
  selectedApplicationId?: string | null;
  resumeVersions: readonly ResumeVersionSummary[];
  onSelectApplication: (applicationId: string) => void;
  onStatusChange?: (applicationId: string, status: ApplicationStatus) => void;
  onCreateApplication?: () => void;
  onEditApplication?: (applicationId: string) => void;
  onOpenVersion?: (resumeVersionId: string) => void;
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "Not set";
  }

  const parsed = new Date(value.includes("T") ? value : `${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

export function ApplicationTracker({
  applications,
  selectedApplicationId,
  resumeVersions,
  onSelectApplication,
  onStatusChange,
  onCreateApplication,
  onEditApplication,
  onOpenVersion,
}: ApplicationTrackerProps) {
  const selectedApplication = applications.find(
    (application) => application.id === selectedApplicationId,
  );

  return (
    <section className="application-tracker" aria-labelledby="applications-heading">
      <header className="application-tracker__header">
        <div>
          <p className="application-tracker__eyebrow">F13</p>
          <h2 id="applications-heading">Applications</h2>
          <p>Track each opportunity and the resume versions saved for it.</p>
        </div>
        {onCreateApplication ? (
          <button type="button" onClick={onCreateApplication}>
            Add application
          </button>
        ) : null}
      </header>

      <div className="application-tracker__layout">
        <div className="application-tracker__list" aria-label="Tracked applications">
          {applications.length === 0 ? (
            <p>No applications tracked yet.</p>
          ) : (
            applications.map((application) => (
              <button
                className="application-tracker__application"
                data-selected={application.id === selectedApplicationId}
                key={application.id}
                type="button"
                onClick={() => onSelectApplication(application.id)}
              >
                <strong>{application.companyName}</strong>
                <span>{application.roleTitle}</span>
                <span>{APPLICATION_STATUS_LABELS[application.status]}</span>
                <span>
                  {application.versionCount} resume version
                  {application.versionCount === 1 ? "" : "s"}
                </span>
              </button>
            ))
          )}
        </div>

        <div className="application-tracker__details">
          {selectedApplication ? (
            <ApplicationDetails
              application={selectedApplication}
              resumeVersions={resumeVersions}
              onStatusChange={onStatusChange}
              onEditApplication={onEditApplication}
              onOpenVersion={onOpenVersion}
            />
          ) : (
            <p>Select an application to view its details.</p>
          )}
        </div>
      </div>
    </section>
  );
}

interface ApplicationDetailsProps {
  application: ApplicationSummary;
  resumeVersions: readonly ResumeVersionSummary[];
  onStatusChange?: (applicationId: string, status: ApplicationStatus) => void;
  onEditApplication?: (applicationId: string) => void;
  onOpenVersion?: (resumeVersionId: string) => void;
}

function ApplicationDetails({
  application,
  resumeVersions,
  onStatusChange,
  onEditApplication,
  onOpenVersion,
}: ApplicationDetailsProps) {
  const allowedStatuses = allowedApplicationStatuses(application.status);
  const canChangeStatus = Boolean(onStatusChange && allowedStatuses.length > 0);

  return (
    <div>
      <div className="application-tracker__detail-header">
        <div>
          <h3>{application.companyName}</h3>
          <p>{application.roleTitle}</p>
        </div>
        <div className="application-tracker__detail-actions">
          {onEditApplication ? (
            <button type="button" onClick={() => onEditApplication(application.id)}>
              Edit application
            </button>
          ) : null}
          <label>
            Status
            <select
              aria-label={`Update status for ${application.companyName}`}
              value={application.status}
              disabled={!canChangeStatus}
              onChange={(event) =>
                onStatusChange?.(
                  application.id,
                  event.currentTarget.value as ApplicationStatus,
                )
              }
            >
              <option value={application.status}>
                {APPLICATION_STATUS_LABELS[application.status]}
              </option>
              {allowedStatuses.map((status) => (
                <option key={status} value={status}>
                  {APPLICATION_STATUS_LABELS[status]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <dl className="application-tracker__metadata">
        <div>
          <dt>Location</dt>
          <dd>{application.location || "Not set"}</dd>
        </div>
        <div>
          <dt>Applied</dt>
          <dd>{formatDate(application.appliedOn)}</dd>
        </div>
        <div>
          <dt>Next action</dt>
          <dd>{formatDate(application.nextActionOn)}</dd>
        </div>
      </dl>

      <section aria-labelledby="resume-versions-heading">
        <h4 id="resume-versions-heading">Resume versions</h4>
        {resumeVersions.length === 0 ? (
          <p>No saved resume versions yet.</p>
        ) : (
          <ol className="application-tracker__versions">
            {resumeVersions.map((version) => (
              <li key={version.id}>
                <button
                  type="button"
                  onClick={() => onOpenVersion?.(version.id)}
                  disabled={!onOpenVersion}
                >
                  <strong>Version {version.versionNumber}</strong>
                  <span>{version.statementCount} statements</span>
                  <span>{formatDate(version.createdAt)}</span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

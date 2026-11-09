import { useEffect, useState } from "react";

import { listResumeVersions } from "../applications/api";
import type { ResumeVersionApiRecord } from "../applications/api";
import { downloadResume, type ResumeExportFormat } from "./api";
import { ResumePreview } from "./ResumePreview";
import "./ResumePage.css";

interface Props {
  token: string;
  applicationId: string;
}

export function ResumePage({ token, applicationId }: Props) {
  const [template, setTemplate] = useState<"standard" | "compact">("standard");
  const [versions, setVersions] = useState<ResumeVersionApiRecord[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError("");
    setVersions([]);
    setSelectedVersionId("");

    void listResumeVersions(token, applicationId)
      .then((records) => {
        if (!active) return;

        const ordered = [...records].sort(
          (a, b) => b.version_number - a.version_number,
        );

        setVersions(ordered);
        setSelectedVersionId(ordered[0]?.id ?? "");
      })
      .catch((cause: unknown) => {
        if (!active) return;

        setError(
          cause instanceof Error
            ? cause.message
            : "Unable to load saved resume versions.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token, applicationId]);

  async function handleDownload(format: ResumeExportFormat) {
    if (!selectedVersionId || downloading || loading) return;

    setDownloading(true);
    setError("");

    try {
      const file = await downloadResume(
        token,
        selectedVersionId,
        format,
        template,
      );

      const url = URL.createObjectURL(file);
      const link = document.createElement("a");

      link.href = url;
      link.download = `applywise-resume.${format}`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      // Release the temporary browser URL after the download starts.
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Unable to download your resume.",
      );
    } finally {
      setDownloading(false);
    }
  }

  return (
    <section className="resume-workspace" aria-labelledby="resume-heading">
      <header className="workspace-heading">
        <p className="workspace-eyebrow">RESUME STUDIO</p>
        <h2 id="resume-heading">Build your resume</h2>
        <p>Choose a clear layout for your approved experience.</p>
      </header>

      <p className="prototype-notice">
        The preview below contains fictional sample content for layout
        demonstration only. Downloaded documents use your selected saved
        resume version and are validated by the server.
      </p>

      <div className="resume-layout">
        <aside className="resume-controls" aria-labelledby="settings-heading">

          <h3 id="settings-heading">Document settings</h3>

          <label htmlFor="resume-version">Resume version</label>

          {loading ? (
            <p role="status">Loading saved resume versions...</p>
          ) : versions.length > 0 ? (
            <select
              id="resume-version"
              value={selectedVersionId}
              onChange={(event) => {
                setSelectedVersionId(event.target.value);
                setError("");
              }}
            >
              {versions.map((version) => (
                <option key={version.id} value={version.id}>
                  Version {version.version_number}
                </option>
              ))}
            </select>
          ) : (
            <p>No saved resume versions are available for this application.</p>
          )}

          <p className="template-description">
            Saved versions are historical records. Export eligibility is
            checked when you download.
          </p>

          <label htmlFor="resume-template">Resume template</label>
          <select
            id="resume-template"
            value={template}
onChange={(event) => {
  const value = event.target.value;

  if (value === "standard" || value === "compact") {
    setTemplate(value);
  }
}}
          >
            <option value="standard">Standard</option>
            <option value="compact">Compact</option>
          </select>

          <p className="template-description">
            {template === "standard"
              ? "Comfortable spacing with clear section headings."
              : "Tighter spacing for a more condensed presentation."}
          </p>

          <p>
            Selected template: {template === "standard" ? "Standard" : "Compact"}
          </p>

          <hr />

          <h3>Export your resume</h3>

          <p id="export-note">
            Downloads use your selected saved resume version and require
            current verification and approval.
          </p>

          {error && (
            <p role="alert" className="resume-export-error">
              {error}
            </p>
          )}

          <div className="export-actions">
            <button
              type="button"
              disabled={loading || downloading || !selectedVersionId}
              aria-describedby="export-note"
              onClick={() => void handleDownload("pdf")}
            >
              {downloading ? "Preparing download..." : "Download PDF"}
            </button>

            <button
              type="button"
              disabled={loading || downloading || !selectedVersionId}
              aria-describedby="export-note"
              onClick={() => void handleDownload("docx")}
            >
              {downloading ? "Preparing download..." : "Download Word"}
            </button>
          </div>

        </aside>

        <section className="preview-area" aria-labelledby="preview-heading">
          <div className="preview-heading">
            <h3 id="preview-heading">Resume preview</h3>
            <span>Sample content</span>
          </div>

          <ResumePreview template={template} />
        </section>
      </div>
    </section>
  );
}

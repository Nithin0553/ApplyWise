import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth";
import {
  buildReviewerShareUrl,
  createShare,
  listOwnedShares,
  listPeerFeedback,
  listShareableResumeVersions,
  revokeShare,
  toPeerFeedbackSummary,
  toShareGrantSummary,
} from "./api";
import { PeerFeedbackPanel } from "./PeerFeedbackPanel";
import { ShareManager } from "./ShareManager";
import type {
  PeerFeedbackSummary,
  ShareableResumeVersion,
  ShareGrantSummary,
} from "./types";

import "./sharing.css";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Sharing request failed.";
}

function expiryToIso(value: string): string | null {
  if (!value.trim()) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error("Enter a valid share expiration date and time.");
  }
  return parsed.toISOString();
}

export function SharingPage() {
  const { token } = useAuth();
  const [shares, setShares] = useState<ShareGrantSummary[]>([]);
  const [resumeVersions, setResumeVersions] = useState<ShareableResumeVersion[]>([]);
  const [selectedResumeVersionId, setSelectedResumeVersionId] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [newShareUrl, setNewShareUrl] = useState<string | null>(null);
  const [selectedShareId, setSelectedShareId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<PeerFeedbackSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const labelMap = useMemo(
    () => new Map(resumeVersions.map((version) => [version.id, version.label])),
    [resumeVersions],
  );

  const load = useCallback(async () => {
    if (!token) {
      setIsLoading(false);
      setError("Sign in as a Job Seeker to manage peer-review links.");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const [shareRecords, versions] = await Promise.all([
        listOwnedShares(token),
        listShareableResumeVersions(token),
      ]);
      const labels = new Map(versions.map((version) => [version.id, version.label]));
      setResumeVersions(versions);
      setShares(shareRecords.map((record) => toShareGrantSummary(record, labels)));
      setSelectedResumeVersionId((current) => current || versions[0]?.id || "");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreateShare() {
    if (!token || !selectedResumeVersionId) return;

    setIsWorking(true);
    setError(null);
    try {
      const created = await createShare(
        token,
        selectedResumeVersionId,
        expiryToIso(expiresAt),
      );
      const summary = toShareGrantSummary(created.grant, labelMap);
      setShares((current) => [summary, ...current.filter((item) => item.id !== summary.id)]);
      setNewShareUrl(buildReviewerShareUrl(created.secret));
      setSelectedShareId(summary.id);
      setFeedback([]);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setIsWorking(false);
    }
  }

  async function handleRevokeShare(shareId: string) {
    if (!token) return;

    setIsWorking(true);
    setError(null);
    try {
      const revoked = await revokeShare(token, shareId);
      const summary = toShareGrantSummary(revoked, labelMap);
      setShares((current) => current.map((item) => (item.id === shareId ? summary : item)));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setIsWorking(false);
    }
  }

  async function handleSelectShare(shareId: string) {
    if (!token) return;

    setSelectedShareId(shareId);
    setError(null);
    try {
      const records = await listPeerFeedback(token, shareId);
      setFeedback(records.map(toPeerFeedbackSummary));
    } catch (requestError) {
      setFeedback([]);
      setError(errorMessage(requestError));
    }
  }

  async function handleCopyShareUrl(shareUrl: string) {
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard access is unavailable. Copy the link manually.");
      }
      await navigator.clipboard.writeText(shareUrl);
    } catch (copyError) {
      setError(errorMessage(copyError));
    }
  }

  const selectedShare = shares.find((share) => share.id === selectedShareId);

  if (isLoading) {
    return <p className="sharing-page__status">Loading peer-review sharing…</p>;
  }

  return (
    <section className="sharing-page">
      <div className="sharing-page__controls" aria-labelledby="share-target-heading">
        <div>
          <p className="sharing-manager__eyebrow">F14 setup</p>
          <h2 id="share-target-heading">Choose a saved resume version</h2>
          <p>Each link grants review access to one immutable F13 resume version only.</p>
        </div>

        {resumeVersions.length > 0 ? (
          <div className="sharing-page__control-grid">
            <label>
              Resume version
              <select
                value={selectedResumeVersionId}
                disabled={isWorking}
                onChange={(event) => setSelectedResumeVersionId(event.currentTarget.value)}
              >
                {resumeVersions.map((version) => (
                  <option key={version.id} value={version.id}>
                    {version.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Expires at (optional)
              <input
                type="datetime-local"
                value={expiresAt}
                disabled={isWorking}
                onChange={(event) => setExpiresAt(event.currentTarget.value)}
              />
            </label>
          </div>
        ) : (
          <p>Save a resume version in Application Tracking before creating a peer-review link.</p>
        )}
      </div>

      {error ? <p className="sharing-page__error" role="alert">{error}</p> : null}

      <ShareManager
        shares={shares}
        newShareUrl={newShareUrl}
        selectedShareId={selectedShareId}
        onCreateShare={resumeVersions.length > 0 && !isWorking ? handleCreateShare : undefined}
        onCopyShareUrl={handleCopyShareUrl}
        onRevokeShare={isWorking ? undefined : handleRevokeShare}
        onSelectShare={handleSelectShare}
      />

      {selectedShare ? (
        <PeerFeedbackPanel
          resumeVersionLabel={selectedShare.resumeVersionLabel}
          feedback={feedback}
        />
      ) : null}
    </section>
  );
}

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth";
import {
  readReviewerShareSecret,
  resolveShare,
  submitPeerFeedback,
  toPeerFeedbackSummary,
  toSharedResumeReference,
} from "./api";
import { PeerFeedbackPanel } from "./PeerFeedbackPanel";
import type { PeerFeedbackSummary, SharedResumeReference } from "./types";

import "./sharing.css";

interface ReviewerSharePageProps {
  secret?: string;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to open this share link.";
}

function formatDate(value?: string | null): string {
  if (!value) return "No expiration";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function ReviewerSharePage({ secret }: ReviewerSharePageProps) {
  const { token } = useAuth();
  const linkedSecret = useMemo(
    () => secret ?? readReviewerShareSecret(),
    [secret],
  );
  const [secretInput, setSecretInput] = useState(linkedSecret ?? "");
  const [resolvedSecret, setResolvedSecret] = useState<string | null>(null);
  const [share, setShare] = useState<SharedResumeReference | null>(null);
  const [submittedFeedback, setSubmittedFeedback] = useState<PeerFeedbackSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openShare = useCallback(
    async (candidateSecret: string) => {
      if (!token) {
        setError("Sign in with a Reviewer account to open a peer-review link.");
        return;
      }

      const normalized = candidateSecret.trim();
      if (normalized.length < 20) {
        setError("Enter the complete peer-review share secret.");
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const record = await resolveShare(token, normalized);
        setShare(toSharedResumeReference(record));
        setResolvedSecret(normalized);
        setSubmittedFeedback([]);
      } catch (requestError) {
        setShare(null);
        setResolvedSecret(null);
        setError(errorMessage(requestError));
      } finally {
        setIsLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    if (linkedSecret) void openShare(linkedSecret);
  }, [linkedSecret, openShare]);

  function handleLookup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void openShare(secretInput);
  }

  async function handleSubmitFeedback(comment: string) {
    if (!token || !resolvedSecret) return;

    setError(null);
    try {
      const record = await submitPeerFeedback(token, resolvedSecret, comment);
      setSubmittedFeedback((current) => [...current, toPeerFeedbackSummary(record)]);
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  return (
    <section className="reviewer-share-page" aria-labelledby="reviewer-share-heading">
      <header>
        <p className="sharing-manager__eyebrow">F14 reviewer</p>
        <h2 id="reviewer-share-heading">Review a shared resume version</h2>
        <p>Access is limited to the immutable version identified by the share link.</p>
      </header>

      {!linkedSecret ? (
        <form className="reviewer-share-page__lookup" onSubmit={handleLookup}>
          <label htmlFor="review-share-secret">Share secret</label>
          <div className="sharing-manager__link-row">
            <input
              id="review-share-secret"
              value={secretInput}
              minLength={20}
              maxLength={200}
              onChange={(event) => setSecretInput(event.currentTarget.value)}
            />
            <button type="submit" disabled={isLoading}>
              Open share
            </button>
          </div>
        </form>
      ) : null}

      {isLoading ? <p className="sharing-page__status">Opening shared version…</p> : null}
      {error ? <p className="sharing-page__error" role="alert">{error}</p> : null}

      {share ? (
        <>
          <article className="reviewer-share-page__reference">
            <h3>Shared resume reference</h3>
            <dl>
              <div>
                <dt>Resume version</dt>
                <dd>{share.resumeVersionId}</dd>
              </div>
              <div>
                <dt>Shared</dt>
                <dd>{formatDate(share.createdAt)}</dd>
              </div>
              <div>
                <dt>Expires</dt>
                <dd>{formatDate(share.expiresAt)}</dd>
              </div>
            </dl>
            <p>
              F10 owns document rendering. F14 intentionally exposes only the version reference
              here and never reconstructs Career Evidence Profile data in the reviewer surface.
            </p>
          </article>

          <PeerFeedbackPanel
            resumeVersionLabel={`Resume version ${share.resumeVersionId.slice(0, 8)}`}
            feedback={submittedFeedback}
            historyHeading="Feedback submitted this session"
            onSubmitFeedback={handleSubmitFeedback}
          />
        </>
      ) : null}
    </section>
  );
}

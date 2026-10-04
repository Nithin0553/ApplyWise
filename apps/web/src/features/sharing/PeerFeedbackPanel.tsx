import { type FormEvent, useState } from "react";

import "./sharing.css";

import type { PeerFeedbackSummary } from "./types";

interface PeerFeedbackPanelProps {
  resumeVersionLabel: string;
  feedback: readonly PeerFeedbackSummary[];
  onSubmitFeedback?: (comment: string) => void;
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function PeerFeedbackPanel({
  resumeVersionLabel,
  feedback,
  onSubmitFeedback,
}: PeerFeedbackPanelProps) {
  const [comment, setComment] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = comment.trim();
    if (!normalized || !onSubmitFeedback) {
      return;
    }

    onSubmitFeedback(normalized);
    setComment("");
  }

  return (
    <section className="peer-feedback" aria-labelledby="peer-feedback-heading">
      <header>
        <p className="peer-feedback__eyebrow">Peer review</p>
        <h2 id="peer-feedback-heading">{resumeVersionLabel}</h2>
        <p>Feedback is attached to this saved resume version and does not edit it directly.</p>
      </header>

      {onSubmitFeedback ? (
        <form className="peer-feedback__form" onSubmit={handleSubmit}>
          <label htmlFor="peer-feedback-comment">Feedback</label>
          <textarea
            id="peer-feedback-comment"
            maxLength={4000}
            rows={5}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
          <button type="submit">Submit feedback</button>
        </form>
      ) : null}

      <div className="peer-feedback__history" aria-label="Peer feedback history">
        <h3>Feedback history</h3>
        {feedback.length === 0 ? (
          <p>No peer feedback has been submitted yet.</p>
        ) : (
          <ul>
            {feedback.map((item) => (
              <li key={item.id}>
                <div className="peer-feedback__meta">
                  <strong>{item.reviewerLabel}</strong>
                  <span>{formatDate(item.createdAt)}</span>
                </div>
                <p>{item.comment}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

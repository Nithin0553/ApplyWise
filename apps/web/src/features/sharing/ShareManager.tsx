import "./sharing.css";

import {
  getShareGrantStatus,
  type ShareGrantStatus,
  type ShareGrantSummary,
} from "./types";

interface ShareManagerProps {
  shares: readonly ShareGrantSummary[];
  newShareUrl?: string | null;
  now?: Date;
  onCreateShare?: () => void;
  onCopyShareUrl?: (shareUrl: string) => void;
  onRevokeShare?: (shareId: string) => void;
}

const STATUS_LABELS: Record<ShareGrantStatus, string> = {
  active: "Active",
  expired: "Expired",
  revoked: "Revoked",
};

function formatDate(value?: string | null): string {
  if (!value) {
    return "No expiration";
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function ShareManager({
  shares,
  newShareUrl,
  now = new Date(),
  onCreateShare,
  onCopyShareUrl,
  onRevokeShare,
}: ShareManagerProps) {
  return (
    <section className="sharing-manager" aria-labelledby="sharing-manager-heading">
      <header className="sharing-manager__header">
        <div>
          <p className="sharing-manager__eyebrow">F14</p>
          <h2 id="sharing-manager-heading">Peer review sharing</h2>
          <p>Share one saved resume version at a time and revoke access when needed.</p>
        </div>
        {onCreateShare ? (
          <button type="button" onClick={onCreateShare}>
            Create share link
          </button>
        ) : null}
      </header>

      {newShareUrl ? (
        <div className="sharing-manager__new-link" role="status">
          <label htmlFor="new-share-link">New share link</label>
          <div className="sharing-manager__link-row">
            <input id="new-share-link" type="text" readOnly value={newShareUrl} />
            {onCopyShareUrl ? (
              <button type="button" onClick={() => onCopyShareUrl(newShareUrl)}>
                Copy link
              </button>
            ) : null}
          </div>
          <p>Save or copy this link now. The share secret is not stored in readable form.</p>
        </div>
      ) : null}

      <div className="sharing-manager__list" aria-label="Resume share links">
        {shares.length === 0 ? (
          <p>No resume versions are currently shared for peer review.</p>
        ) : (
          shares.map((share) => {
            const status = getShareGrantStatus(share, now);
            return (
              <article className="sharing-manager__share" key={share.id}>
                <div>
                  <h3>{share.resumeVersionLabel}</h3>
                  <p>Created {formatDate(share.createdAt)}</p>
                  <p>Expires {formatDate(share.expiresAt)}</p>
                </div>
                <div className="sharing-manager__actions">
                  <span data-status={status}>{STATUS_LABELS[status]}</span>
                  {status === "active" && onRevokeShare ? (
                    <button
                      type="button"
                      aria-label={`Revoke ${share.resumeVersionLabel}`}
                      onClick={() => onRevokeShare(share.id)}
                    >
                      Revoke
                    </button>
                  ) : null}
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}

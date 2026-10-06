import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth/AuthContext";
import {
  EvidenceApiError,
  approveEvidence,
  createEvidence,
  listEvidence,
  unconfirmEvidence,
  updateEvidence,
} from "./api";
import { EvidenceForm } from "./EvidenceForm";
import "./evidence.css";
import { evidenceTypeLabel, toEvidenceFormValues } from "./types";
import type { EvidenceFormValues, EvidenceItem, EvidenceStatus } from "./types";

type EvidenceFilter = "all" | EvidenceStatus;

function errorMessage(error: unknown): string {
  if (error instanceof EvidenceApiError) {
    return error.message;
  }
  return "Something went wrong while updating your evidence. Please try again.";
}

function replaceEvidence(items: EvidenceItem[], replacement: EvidenceItem): EvidenceItem[] {
  return items.map((item) => (item.id === replacement.id ? replacement : item));
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Not set";
  }
  const parsed = new Date(value.includes("T") ? value : `${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

function EvidenceCard({
  item,
  busy,
  onEdit,
  onApprove,
  onUnconfirm,
}: {
  item: EvidenceItem;
  busy: boolean;
  onEdit: (item: EvidenceItem) => void;
  onApprove: (item: EvidenceItem) => void;
  onUnconfirm: (item: EvidenceItem) => void;
}) {
  return (
    <article className="evidence-card">
      <div className="evidence-card__header">
        <div>
          <p className="evidence-card__type">{evidenceTypeLabel(item.evidenceType)}</p>
          <h3>{item.title}</h3>
        </div>
        <span className={`evidence-status evidence-status--${item.status}`}>
          {item.status === "approved" ? "Approved" : "Unconfirmed"}
        </span>
      </div>

      {item.organization || item.role ? (
        <p className="evidence-card__summary">
          {[item.role, item.organization].filter(Boolean).join(" · ")}
        </p>
      ) : null}

      {item.description ? <p>{item.description}</p> : null}

      <dl className="evidence-card__metadata">
        {item.location ? (
          <div>
            <dt>Location</dt>
            <dd>{item.location}</dd>
          </div>
        ) : null}
        {item.skillName ? (
          <div>
            <dt>Skill</dt>
            <dd>{item.skillName}</dd>
          </div>
        ) : null}
        {item.proficiency ? (
          <div>
            <dt>Proficiency</dt>
            <dd>{item.proficiency}</dd>
          </div>
        ) : null}
        {item.credential ? (
          <div>
            <dt>Credential</dt>
            <dd>{item.credential}</dd>
          </div>
        ) : null}
        {item.startDate || item.endDate ? (
          <div>
            <dt>Dates</dt>
            <dd>
              {formatDate(item.startDate)} – {item.endDate ? formatDate(item.endDate) : "Present"}
            </dd>
          </div>
        ) : null}
        {item.source ? (
          <div>
            <dt>Source</dt>
            <dd>{item.source}</dd>
          </div>
        ) : null}
      </dl>

      {item.url ? (
        <a className="evidence-card__link" href={item.url} target="_blank" rel="noreferrer">
          Open supporting link
        </a>
      ) : null}

      <p className="evidence-card__approval-note">
        {item.status === "approved"
          ? `Approved ${formatDate(item.approvedAt)}. This evidence can be used for grounded generation.`
          : "Review and approve this evidence before it can be used for grounded generation."}
      </p>

      <div className="evidence-card__actions">
        <button type="button" onClick={() => onEdit(item)} disabled={busy}>
          Edit
        </button>
        {item.status === "approved" ? (
          <button type="button" onClick={() => onUnconfirm(item)} disabled={busy}>
            Mark unconfirmed
          </button>
        ) : (
          <button type="button" onClick={() => onApprove(item)} disabled={busy}>
            Approve evidence
          </button>
        )}
      </div>
    </article>
  );
}

export function EvidenceManager({ token }: { token: string }) {
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [filter, setFilter] = useState<EvidenceFilter>("all");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [busyEvidenceId, setBusyEvidenceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [editingItem, setEditingItem] = useState<EvidenceItem | null>(null);

  const loadEvidence = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setItems(await listEvidence(token));
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadEvidence();
  }, [loadEvidence]);

  const counts = useMemo(
    () => ({
      all: items.length,
      unconfirmed: items.filter((item) => item.status === "unconfirmed").length,
      approved: items.filter((item) => item.status === "approved").length,
    }),
    [items],
  );

  const visibleItems = useMemo(
    () => (filter === "all" ? items : items.filter((item) => item.status === filter)),
    [filter, items],
  );

  async function handleCreate(values: EvidenceFormValues) {
    setIsSaving(true);
    setError(null);
    try {
      const created = await createEvidence(token, values);
      setItems((current) => [...current, created]);
      setIsCreating(false);
      setFilter("all");
    } catch (createError) {
      setError(errorMessage(createError));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleUpdate(values: EvidenceFormValues) {
    if (!editingItem) {
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const updated = await updateEvidence(token, editingItem.id, values);
      setItems((current) => replaceEvidence(current, updated));
      setEditingItem(null);
    } catch (updateError) {
      setError(errorMessage(updateError));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleApprove(item: EvidenceItem) {
    setBusyEvidenceId(item.id);
    setError(null);
    try {
      const approved = await approveEvidence(token, item.id);
      setItems((current) => replaceEvidence(current, approved));
    } catch (approveError) {
      setError(errorMessage(approveError));
    } finally {
      setBusyEvidenceId(null);
    }
  }

  async function handleUnconfirm(item: EvidenceItem) {
    setBusyEvidenceId(item.id);
    setError(null);
    try {
      const unconfirmed = await unconfirmEvidence(token, item.id);
      setItems((current) => replaceEvidence(current, unconfirmed));
    } catch (unconfirmError) {
      setError(errorMessage(unconfirmError));
    } finally {
      setBusyEvidenceId(null);
    }
  }

  function beginCreate() {
    setEditingItem(null);
    setIsCreating(true);
    setError(null);
  }

  function beginEdit(item: EvidenceItem) {
    setIsCreating(false);
    setEditingItem(item);
    setError(null);
  }

  function closeForm() {
    setIsCreating(false);
    setEditingItem(null);
  }

  return (
    <section className="evidence-profile" aria-labelledby="evidence-heading">
      <header className="evidence-profile__header">
        <div>
          <p className="evidence-profile__eyebrow">F02 · Career Evidence Profile</p>
          <h2 id="evidence-heading">Career evidence</h2>
          <p>
            Keep the facts that ApplyWise is allowed to use. New and edited evidence stays
            unconfirmed until you explicitly approve it.
          </p>
        </div>
        <button type="button" onClick={beginCreate} disabled={isSaving || isCreating}>
          Add evidence
        </button>
      </header>

      <div className="evidence-profile__filters" aria-label="Filter career evidence">
        <button
          type="button"
          data-selected={filter === "all"}
          onClick={() => setFilter("all")}
        >
          All ({counts.all})
        </button>
        <button
          type="button"
          data-selected={filter === "unconfirmed"}
          onClick={() => setFilter("unconfirmed")}
        >
          Unconfirmed ({counts.unconfirmed})
        </button>
        <button
          type="button"
          data-selected={filter === "approved"}
          onClick={() => setFilter("approved")}
        >
          Approved ({counts.approved})
        </button>
      </div>

      {error ? (
        <div className="evidence-profile__error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => void loadEvidence()} disabled={isLoading}>
            Reload
          </button>
        </div>
      ) : null}

      {isCreating ? (
        <section className="evidence-editor" aria-labelledby="new-evidence-heading">
          <h3 id="new-evidence-heading">Add career evidence</h3>
          <EvidenceForm
            busy={isSaving}
            onSubmit={handleCreate}
            onCancel={closeForm}
          />
        </section>
      ) : null}

      {editingItem ? (
        <section className="evidence-editor" aria-labelledby="edit-evidence-heading">
          <h3 id="edit-evidence-heading">Edit career evidence</h3>
          <EvidenceForm
            key={editingItem.id}
            initialValues={toEvidenceFormValues(editingItem)}
            submitLabel="Save changes"
            busy={isSaving}
            approvalWillBeRevoked={editingItem.status === "approved"}
            onSubmit={handleUpdate}
            onCancel={closeForm}
          />
        </section>
      ) : null}

      {isLoading ? <p className="evidence-profile__state">Loading career evidence...</p> : null}

      {!isLoading && visibleItems.length === 0 ? (
        <div className="evidence-profile__empty">
          <h3>{items.length === 0 ? "No career evidence yet" : "No evidence in this view"}</h3>
          <p>
            {items.length === 0
              ? "Add work, education, project, skill, certification, responsibility, accomplishment, or supporting-detail evidence to begin."
              : "Choose another filter to see your other evidence records."}
          </p>
        </div>
      ) : null}

      {!isLoading && visibleItems.length > 0 ? (
        <div className="evidence-profile__list">
          {visibleItems.map((item) => (
            <EvidenceCard
              key={item.id}
              item={item}
              busy={busyEvidenceId === item.id || isSaving}
              onEdit={beginEdit}
              onApprove={(value) => void handleApprove(value)}
              onUnconfirm={(value) => void handleUnconfirm(value)}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function EvidenceProfilePage() {
  const { token, user } = useAuth();

  if (!token || !user) {
    return <p>Sign in to manage your Career Evidence Profile.</p>;
  }

  if (user.role !== "job_seeker") {
    return <p>The Career Evidence Profile is available to Job Seeker accounts.</p>;
  }

  return <EvidenceManager token={token} />;
}

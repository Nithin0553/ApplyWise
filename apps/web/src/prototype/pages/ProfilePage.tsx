import type { PageProps } from "../Shell";
import { useAuth } from "../../features/auth";

/**
 * Account profile.
 *
 * Shows the fields the backend actually stores today: name, email, role and
 * the date the account was created, all from `GET /auth/me`.
 *
 * The wider profile the product needs — contact details, headline, summary,
 * skills, education, links — has no columns and no write endpoint yet, so it
 * is named here as unavailable rather than rendered as a form that silently
 * discards what the user types. The backend work required is listed in the
 * feature README; when `PATCH /auth/me` exists, the read-only rows below
 * become fields and this page keeps its shape.
 */

const ROLE_LABELS: Record<string, string> = {
  job_seeker: "Job seeker",
  administrator: "Administrator",
};

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="sf-detail">
      <dt>{label}</dt>
      <dd>{value || "—"}</dd>
    </div>
  );
}

export function ProfilePage({ go }: PageProps) {
  const { user } = useAuth();

  if (!user) {
    return (
      <main className="sf-page sf-reveal">
        <header className="sf-pagehead">
          <h2 className="sf-h2">Profile</h2>
        </header>
        <div className="sf-card sf-empty">
          <p style={{ margin: 0 }}>Sign in to view your profile.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="sf-page sf-reveal">
      <header className="sf-pagehead">
        <h2 className="sf-h2">Profile</h2>
        <p className="sf-lede">Manage the information used across your ApplyWise account.</p>
      </header>

      <section className="sf-card" aria-labelledby="account-heading" style={{ marginBottom: 24 }}>
        <h3 className="sf-h3" id="account-heading">
          Account
        </h3>
        <dl className="sf-details">
          <Row label="Full name" value={user.full_name} />
          <Row label="Email address" value={user.email} />
          <Row label="Account type" value={ROLE_LABELS[user.role] ?? user.role} />
          <Row label="Member since" value={formatDate(user.created_at)} />
        </dl>
      </section>

      <section className="sf-card" aria-labelledby="details-heading">
        <h3 className="sf-h3" id="details-heading">
          Professional details
        </h3>
        <p className="sf-muted" style={{ marginTop: 8, lineHeight: 1.6 }}>
          Contact details, professional headline, skills, education and links are not yet
          available on your account. Career history you want used in generated statements is
          managed as evidence.
        </p>
        <button type="button" className="sf-btn sf-btn-primary sf-btn-sm" onClick={() => go("evidence")}>
          Manage evidence
        </button>
      </section>
    </main>
  );
}

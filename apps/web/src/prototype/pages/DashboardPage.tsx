import { useCallback, useEffect, useState } from "react";

import type { PageProps } from "../Shell";
import { useAuth } from "../../features/auth";
import { listApplications, type ApplicationApiRecord } from "../../features/applications";
import { fetchApprovedEvidence } from "../../features/tailoring/api";
import { APPLICATIONS, EVIDENCE } from "../mock";

/**
 * The signed-in landing page.
 *
 * Every number here is read from the backend. Where an endpoint does not exist
 * yet, or returns nothing, the card shows an empty state and a way to act on
 * it — it never shows an invented figure.
 */

interface Summary {
  approvedEvidence: number | null;
  applications: ApplicationApiRecord[] | null;
}

const EMPTY: Summary = { approvedEvidence: null, applications: null };

function Metric({
  label,
  value,
  empty,
  action,
  onAction,
}: {
  label: string;
  value: number | null;
  empty: string;
  action: string;
  onAction: () => void;
}) {
  const hasValue = value !== null && value > 0;
  return (
    <article className="sf-card sf-metric">
      <p className="sf-metric__label">{label}</p>
      {hasValue ? (
        <p className="sf-metric__value">{value}</p>
      ) : (
        <p className="sf-metric__empty">{empty}</p>
      )}
      <button type="button" className="sf-btn sf-btn-ghost sf-btn-sm" onClick={onAction}>
        {action}
      </button>
    </article>
  );
}

export function DashboardPage({ go, demo = false }: PageProps & { demo?: boolean }) {
  const { token, user } = useAuth();
  const [summary, setSummary] = useState<Summary>(EMPTY);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (demo || !token) {
      setSummary(EMPTY);
      return;
    }
    setLoading(true);

    // Each source is settled on its own: one unavailable endpoint must not
    // blank the whole dashboard.
    const [evidence, applications] = await Promise.allSettled([
      fetchApprovedEvidence(token),
      listApplications(token),
    ]);

    setSummary({
      approvedEvidence: evidence.status === "fulfilled" ? evidence.value.length : null,
      applications: applications.status === "fulfilled" ? applications.value : null,
    });
    setLoading(false);
  }, [token, demo]);

  useEffect(() => {
    void load();
  }, [load]);

  const applications = summary.applications ?? [];
  const approvedEvidence = demo
    ? EVIDENCE.filter((item) => item.status === "APPROVED").length
    : summary.approvedEvidence;
  const applicationCount = demo ? APPLICATIONS.length : summary.applications?.length ?? null;
  const recent = demo
    ? APPLICATIONS.slice(0, 4).map((item) => ({
        id: item.company,
        company_name: item.company,
        role_title: item.role,
        status: item.stage,
      }))
    : applications.slice(0, 4);
  const firstName = demo ? "" : (user?.full_name ?? "").trim().split(" ")[0];

  return (
    <main className="sf-page sf-reveal">
      <header className="sf-pagehead">
        <h2 className="sf-h2">{firstName ? `Welcome back, ${firstName}` : "Dashboard"}</h2>
        <p className="sf-lede">
          Approve career evidence, analyse a job description, and generate statements you can
          support.
        </p>
      </header>

      <section aria-labelledby="summary-heading" style={{ marginBottom: 40 }}>
        <h3 className="sf-h3" id="summary-heading">
          {demo ? "Sample overview" : "Your account"}
        </h3>
        <div className="sf-grid sf-grid-3" style={{ marginTop: 16 }}>
          <Metric
            label="Approved evidence"
            value={approvedEvidence}
            empty={loading ? "Loading…" : "No approved evidence yet"}
            action="Manage evidence"
            onAction={() => go("evidence")}
          />
          <Metric
            label="Applications tracked"
            value={applicationCount}
            empty={loading ? "Loading…" : "No applications added yet"}
            action="Open applications"
            onAction={() => go("tracker")}
          />
          <article className="sf-card sf-metric">
            <p className="sf-metric__label">Next step</p>
            <p className="sf-metric__empty">
              {approvedEvidence && approvedEvidence > 0
                ? "Analyse a job description, then generate tailored statements."
                : "Add and approve evidence before generating statements."}
            </p>
            <button
              type="button"
              className="sf-btn sf-btn-primary sf-btn-sm"
              onClick={() =>
                go(approvedEvidence && approvedEvidence > 0 ? "jobs" : "evidence")
              }
            >
              {approvedEvidence && approvedEvidence > 0
                ? "Analyse a job"
                : "Add evidence"}
            </button>
          </article>
        </div>
      </section>

      <section aria-labelledby="recent-heading">
        <h3 className="sf-h3" id="recent-heading">
          Recent applications
        </h3>
        {recent.length === 0 ? (
          <div className="sf-card sf-empty" style={{ marginTop: 16 }}>
            <p style={{ margin: 0 }}>No applications added yet.</p>
            <button type="button" className="sf-btn sf-btn-ghost sf-btn-sm" onClick={() => go("tracker")}>
              Add an application
            </button>
          </div>
        ) : (
          <table className="sf-table" style={{ marginTop: 16 }}>
            <caption className="sf-sr">Your most recent applications</caption>
            <thead>
              <tr>
                <th scope="col">Company</th>
                <th scope="col">Role</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((application) => (
                <tr key={application.id}>
                  <td>{application.company_name}</td>
                  <td>{application.role_title}</td>
                  <td>{application.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

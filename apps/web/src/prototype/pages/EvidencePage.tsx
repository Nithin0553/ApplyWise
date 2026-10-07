import { useState } from "react";

import type { PageProps } from "../Shell";
import { EVIDENCE } from "../mock";

export function EvidencePage({ go }: PageProps) {
  const [items, setItems] = useState(EVIDENCE);

  const approved = items.filter((item) => item.status === "APPROVED").length;
  const unconfirmed = items.length - approved;

  function confirm(id: string) {
    setItems((current) =>
      current.map((item) => (item.id === id ? { ...item, status: "APPROVED" as const } : item)),
    );
  }

  return (
    <main className="sf-page sf-reveal">
      <header className="sf-pagehead">
        <h2 className="sf-h2">Career evidence</h2>
        <p className="sf-lede">
          Only approved evidence can be used to write resume content. Imported items start
          unconfirmed until you review them.
        </p>
      </header>

      <div className="sf-grid sf-grid-4" style={{ marginBottom: 24 }}>
        <div className="sf-card sf-card-tight sf-card-sage">
          <div className="sf-eyebrow">Approved</div>
          <div className="sf-stat">{approved}</div>
        </div>
        <div className="sf-card sf-card-tight">
          <div className="sf-eyebrow">Unconfirmed</div>
          <div className="sf-stat">{unconfirmed}</div>
        </div>
        <div className="sf-card sf-card-tight sf-card-lav">
          <div className="sf-eyebrow">Types</div>
          <div className="sf-stat">4</div>
        </div>
        <div className="sf-card sf-card-tight">
          <div className="sf-eyebrow">Last import</div>
          <p style={{ fontSize: 16, margin: "10px 0 0" }}>resume_2026.pdf</p>
        </div>
      </div>

      {unconfirmed > 0 && (
        <div className="sf-banner sf-banner-warn" style={{ marginBottom: 20 }}>
          {unconfirmed} imported item{unconfirmed === 1 ? "" : "s"} still unconfirmed. Generation
          cannot use them until you confirm.
        </div>
      )}

      <div className="sf-stack">
        {items.map((item) => (
          <article className="sf-card" key={item.id}>
            <div className="sf-row" style={{ justifyContent: "space-between" }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ marginBottom: 6 }}>
                  <span className="sf-chip">{item.ref}</span>
                  <span
                    className={
                      item.status === "APPROVED" ? "sf-pill sf-pill-ok" : "sf-pill sf-pill-warn"
                    }
                  >
                    {item.status}
                  </span>
                  <span className="sf-muted">{item.type}</span>
                </div>
                <h3 className="sf-h3">{item.title}</h3>
                <div className="sf-muted">
                  {[item.organization, item.dates].filter(Boolean).join(" · ")}
                </div>
                <p style={{ margin: "10px 0 0", lineHeight: 1.6, maxWidth: 640 }}>{item.detail}</p>
              </div>
              <div className="sf-stack" style={{ gap: 8 }}>
                {item.status === "UNCONFIRMED" ? (
                  <button
                    type="button"
                    className="sf-btn sf-btn-primary"
                    onClick={() => confirm(item.id)}
                  >
                    Confirm and approve
                  </button>
                ) : (
                  <button type="button" className="sf-btn sf-btn-ghost">
                    Edit
                  </button>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="sf-row" style={{ justifyContent: "space-between", marginTop: 28 }}>
        <p className="sf-muted" style={{ margin: 0, alignSelf: "center" }}>
          Editing an approved item sends it back to unconfirmed — approval applies to the words,
          not the row.
        </p>
        <button type="button" className="sf-btn sf-btn-dark" onClick={() => go("jobs")}>
          Next: add a job →
        </button>
      </div>
    </main>
  );
}

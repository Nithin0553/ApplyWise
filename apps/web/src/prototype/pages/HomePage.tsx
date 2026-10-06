import type { PageProps } from "../Shell";
import { DIARY, FAQ } from "../mock";

const SCENARIOS = [
  { when: "Sunday, 9pm", what: "Five tabs open, same resume, five job posts." },
  { when: "Tuesday, lunch", what: "A role you actually want, closing on Friday." },
  { when: "Thursday, late", what: "Did I really say I improved it by 40%?" },
  { when: "Interview day", what: "Every line on the page, you can explain." },
];

export function HomePage({ go }: PageProps) {
  return (
    <main className="sf-page sf-reveal">
      <div
        className="sf-blob"
        style={{ width: 360, height: 360, background: "#ffe4e1", top: 40, left: -80 }}
      />
      <div
        className="sf-blob"
        style={{ width: 320, height: 320, background: "#e6e6fa", top: 180, right: -60 }}
      />

      <section style={{ textAlign: "center", position: "relative", padding: "32px 0 64px" }}>
        <p className="sf-eyebrow">Resume tailoring, grounded in what you did</p>
        <h2 className="sf-h1" style={{ margin: "16px auto", maxWidth: 820 }}>
          Every line on your resume, <span className="sf-cursive">traceable</span> to something
          you actually did.
        </h2>
        <p className="sf-lede" style={{ margin: "16px auto 0" }}>
          ApplyWise writes from career evidence you have approved, shows which evidence each
          sentence came from, and blocks anything it cannot support.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 32 }}>
          <button type="button" className="sf-btn sf-btn-primary" onClick={() => go("evidence")}>
            Start with your evidence
          </button>
          <button type="button" className="sf-btn sf-btn-ghost" onClick={() => go("tailor")}>
            See it tailor a resume
          </button>
        </div>
      </section>

      <section style={{ marginBottom: 64 }}>
        <h3 className="sf-h3" style={{ marginBottom: 16 }}>
          The moments this is for
        </h3>
        <div className="sf-scroll">
          {SCENARIOS.map((item) => (
            <article key={item.when} className="sf-card sf-card-tight" style={{ height: 120 }}>
              <div className="sf-muted">{item.when}</div>
              <p style={{ fontSize: 18, margin: "8px 0 0", lineHeight: 1.4 }}>{item.what}</p>
            </article>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 72 }}>
        <h3 className="sf-h2">How it works</h3>
        <div className="sf-grid sf-grid-3" style={{ marginTop: 24 }}>
          <article className="sf-card sf-card-sage">
            <div className="sf-eyebrow">One</div>
            <h4 className="sf-h3" style={{ marginTop: 8 }}>
              Approve your evidence
            </h4>
            <p className="sf-muted" style={{ lineHeight: 1.6 }}>
              Add roles, projects and skills. Nothing is used until you mark it approved.
            </p>
          </article>
          <article className="sf-card sf-card-lav">
            <div className="sf-eyebrow">Two</div>
            <h4 className="sf-h3" style={{ marginTop: 8 }}>
              Paste a job
            </h4>
            <p className="sf-muted" style={{ lineHeight: 1.6 }}>
              ApplyWise reads the posting, then shows which requirements your evidence covers.
            </p>
          </article>
          <article className="sf-card">
            <div className="sf-eyebrow">Three</div>
            <h4 className="sf-h3" style={{ marginTop: 8 }}>
              Review, approve, export
            </h4>
            <p className="sf-muted" style={{ lineHeight: 1.6 }}>
              Each statement carries its sources. Unsupported claims never reach the page.
            </p>
          </article>
        </div>
      </section>

      <section style={{ marginBottom: 72 }}>
        <h3 className="sf-h2">What it feels like to use</h3>
        <div className="sf-phones" style={{ marginTop: 32 }}>
          <div className="sf-phone sf-phone-l">
            <div className="sf-eyebrow">Evidence</div>
            <p style={{ fontSize: 15, lineHeight: 1.5 }}>
              18 approved, 6 waiting for you to confirm.
            </p>
          </div>
          <div className="sf-phone sf-phone-mid">
            <div className="sf-eyebrow">Tailoring</div>
            <p style={{ fontSize: 16, lineHeight: 1.5, marginTop: 8 }}>
              Built and maintained automated regression suites.
            </p>
            <span className="sf-chip">E1</span>
            <div style={{ marginTop: 24 }}>
              <span className="sf-pill sf-pill-cand">Candidate</span>
              <span className="sf-pill sf-pill-quiet">Not exportable</span>
            </div>
          </div>
          <div className="sf-phone sf-phone-r">
            <div className="sf-eyebrow">Review</div>
            <p style={{ fontSize: 15, lineHeight: 1.5 }}>
              Two verified, one inferred, one blocked.
            </p>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: 72 }}>
        <h3 className="sf-h2">From the people using it</h3>
        <div className="sf-grid sf-grid-2" style={{ marginTop: 24 }}>
          {DIARY.map((entry) => (
            <article key={entry.who} className="sf-note">
              <p style={{ fontSize: 18, lineHeight: 1.6, margin: 0 }}>{entry.quote}</p>
              <div className="sf-sign">
                <hr />
                <span>{entry.who}</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 72 }}>
        <h3 className="sf-h2">Questions</h3>
        <div style={{ marginTop: 24 }}>
          {FAQ.map((item) => (
            <details className="sf-faq" key={item.q}>
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="sf-card" style={{ textAlign: "center", padding: 48 }}>
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 16,
            background: "#292524",
            margin: "0 auto 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          aria-hidden="true"
        >
          <span style={{ width: 10, height: 10, borderRadius: 5, background: "#ffb7b2" }} />
        </div>
        <h3 className="sf-h2">Keep your evidence close</h3>
        <p className="sf-lede" style={{ margin: "12px auto 24px" }}>
          Team Islanders is building this application. Leave an email and we will tell you
          when the first release is ready.
        </p>
        <form
          style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}
          onSubmit={(event) => event.preventDefault()}
        >
          <label className="sf-sr" htmlFor="waitlist">
            Email address
          </label>
          <input
            id="waitlist"
            type="email"
            placeholder="you@example.edu"
            style={{
              borderRadius: 999,
              border: "1px solid #e7e5e4",
              padding: "12px 20px",
              font: "inherit",
              background: "#fafaf9",
              minWidth: 260,
            }}
          />
          <button type="submit" className="sf-btn sf-btn-dark">
            Join the waitlist
          </button>
        </form>
      </section>
    </main>
  );
}

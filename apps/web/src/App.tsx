import { useEffect, useState } from "react";

import { AuthProvider, LoginForm, RegisterForm, useAuth } from "./features/auth";
import { GuidedJourney } from "./features/journey/GuidedJourney";
import { ReviewerSharePage, readReviewerShareSecret } from "./features/sharing";
import "./features/journey/journey.css";
import "./prototype/softly.css";
import "./features/auth/auth-theme.css";
import "./features/journey/storyboard.css";
import "./features/sharing/shell.css";

function AuthGate() {
  const { user, token, isLoading, logout } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [intro, setIntro] = useState(true);
  const [leaving, setLeaving] = useState(false);
  const [enterJourney, setEnterJourney] = useState(false);
  const [reviewerSecret, setReviewerSecret] = useState<string | null>(() => readReviewerShareSecret());

  useEffect(() => {
    // The fragment is captured in memory and removed before login is shown.
    // Never persist a bearer share secret in history, cookies or storage.
    const consumeFragment = () => {
      const incoming = readReviewerShareSecret();
      if (!incoming) return;
      setReviewerSecret(incoming);
      window.history.replaceState(
        window.history.state, "",
        window.location.pathname + window.location.search,
      );
    };
    consumeFragment();
    window.addEventListener("hashchange", consumeFragment);
    return () => window.removeEventListener("hashchange", consumeFragment);
  }, []);

  useEffect(() => {
    const move = window.setTimeout(() => setLeaving(true), 1400);
    const done = window.setTimeout(() => setIntro(false), 2050);
    return () => {
      window.clearTimeout(move);
      window.clearTimeout(done);
    };
  }, []);

  useEffect(() => {
    if (!user || !token) {
      setEnterJourney(false);
      return;
    }
    const next = window.setTimeout(() => setEnterJourney(true), 480);
    return () => window.clearTimeout(next);
  }, [user, token]);

  if (intro) {
    return <main className={`aw-splash ${leaving ? "is-leaving" : ""}`} aria-label="ApplyWise welcome">
      <strong>ApplyWise</strong>
    </main>;
  }

  if (isLoading) {
    return <div className="sf sf-auth"><p className="sf-muted">Loading…</p></div>;
  }

  if (user && token && enterJourney) {
    if (user.role === "reviewer") {
      return <div className="aw-journey aw-reviewer-shell">
        <header className="aw-topbar">
          <strong className="aw-reviewer-wordmark">ApplyWise</strong>
          <button type="button" className="aw-reviewer-logout" onClick={logout}>Log out</button>
        </header>
        <main className="aw-f14-workspace" aria-label="Reviewer access">
          <ReviewerSharePage secret={reviewerSecret ?? undefined} />
        </main>
      </div>;
    }
    if (reviewerSecret) {
      return <main className="aw-journey aw-reviewer-role-notice">
        <h2>A reviewer account is required.</h2>
        <p>This share link is restricted to a provisioned ApplyWise reviewer. Your current account cannot access it.</p>
        <div className="aw-reviewer-notice-actions">
          <button type="button" onClick={logout}>Log out and sign in as a reviewer</button>
          <button type="button" onClick={() => setReviewerSecret(null)}>Return to my workspace</button>
        </div>
      </main>;
    }
    return <GuidedJourney user={user} token={token} logout={logout} />;
  }

  return <div className={`sf sf-auth aw-auth-shell ${user && token ? "aw-auth-leave" : "aw-auth-enter"}`}>
    <div className="sf-auth-card">
      <h1 className="aw-auth-wordmark">
        <span className="aw-auth-wordmark-light" data-text="ApplyWise">ApplyWise</span>
      </h1>
      <p className="sf-auth-tagline">Resume tailoring, grounded in what you actually did.</p>
      {mode === "login"
        ? <LoginForm onSwitchToRegister={() => setMode("register")} />
        : <RegisterForm onSwitchToLogin={() => setMode("login")} />}
    </div>
  </div>;
}

export function App() {
  return <AuthProvider><AuthGate /></AuthProvider>;
}

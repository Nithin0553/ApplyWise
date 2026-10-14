import { useEffect, useState } from "react";

import { AuthProvider, LoginForm, RegisterForm, useAuth } from "./features/auth";
import { GuidedJourney } from "./features/journey/GuidedJourney";
import "./features/journey/journey.css";
import "./prototype/softly.css";
import "./features/auth/auth-theme.css";
import "./features/journey/storyboard.css";

function AuthGate() {
  const { user, token, isLoading, logout } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [intro, setIntro] = useState(true);
  const [leaving, setLeaving] = useState(false);
  const [enterJourney, setEnterJourney] = useState(false);

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

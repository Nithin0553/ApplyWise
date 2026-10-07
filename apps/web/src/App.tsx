import { useState } from "react";

import { AuthProvider, LoginForm, RegisterForm, useAuth } from "./features/auth";
import { Shell } from "./prototype/Shell";

function AuthGate() {
  const { user, isLoading } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");

  if (isLoading) {
    return (
      <div className="sf sf-auth">
        <p className="sf-muted">Loading…</p>
      </div>
    );
  }

  // Signed in: the feature shell takes over. Signed out: F01 owns the screen.
  if (user) {
    return <Shell />;
  }

  // F01 owns the form itself. The frame around it belongs to the shell, so the
  // signed-out screen is themed without reaching into another feature's code.
  return (
    <div className="sf sf-auth">
      <div className="sf-auth-card">
        <div className="sf-logo sf-auth-brand">
          <span className="sf-logo-dot" />
          ApplyWise
        </div>
        <p className="sf-auth-tagline">
          Resume tailoring, grounded in what you actually did.
        </p>
        {mode === "login" ? (
          <LoginForm onSwitchToRegister={() => setMode("register")} />
        ) : (
          <RegisterForm onSwitchToLogin={() => setMode("login")} />
        )}
      </div>
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  );
}

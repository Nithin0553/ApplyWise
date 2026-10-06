import { useState } from "react";

import { AuthProvider, LoginForm, RegisterForm, useAuth } from "./features/auth";

function AuthenticatedPanel() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="session-panel">
      <p>
        Signed in as <strong>{user.full_name}</strong> ({user.email}) · role:{" "}
        <code>{user.role}</code>
      </p>
      <button type="button" onClick={logout}>
        Sign out
      </button>
    </div>
  );
}

function AuthGate() {
  const { user, isLoading } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");

  if (isLoading) {
    return <p>Loading…</p>;
  }

  if (user) {
    return <AuthenticatedPanel />;
  }

  return mode === "login" ? (
    <LoginForm onSwitchToRegister={() => setMode("register")} />
  ) : (
    <RegisterForm onSwitchToLogin={() => setMode("login")} />
  );
}

export function App() {
  return (
    <AuthProvider>
      <main className="shell">
        <h1>ApplyWise</h1>
        <p>Engineering foundation initialized. Feature implementation starts with F01.</p>
        <AuthGate />
      </main>
    </AuthProvider>
  );
}

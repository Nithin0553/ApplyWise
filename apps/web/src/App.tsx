import { useState } from "react";

import { AuthProvider, LoginForm, RegisterForm, useAuth } from "./features/auth";
import { Shell } from "./prototype/Shell";

function AuthGate() {
  const { user, isLoading } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");

  if (isLoading) {
    return <p>Loading…</p>;
  }

  // Signed in: the feature shell takes over. Signed out: F01 owns the screen.
  if (user) {
    return <Shell />;
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
      <AuthGate />
    </AuthProvider>
  );
}

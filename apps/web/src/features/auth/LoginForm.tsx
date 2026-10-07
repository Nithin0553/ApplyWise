// F01: login form.

import { useState } from "react";
import type { FormEvent } from "react";

import { useAuth } from "./AuthContext";

interface LoginFormProps {
  onLoggedIn?: () => void;
  onSwitchToRegister?: () => void;
}

export function LoginForm({ onLoggedIn, onSwitchToRegister }: LoginFormProps) {
  const { login, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await login({ email, password });
      onLoggedIn?.();
    } catch {
      // Error state is surfaced via `error` from useAuth().
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <h2>Sign in to ApplyWise</h2>

      <label htmlFor="login-email">Email</label>
      <input
        id="login-email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />

      <label htmlFor="login-password">Password</label>
      <div className="auth-form__password">
        <input
          id="login-password"
          name="password"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button
          type="button"
          className="auth-form__reveal"
          onClick={() => setShowPassword((current) => !current)}
          aria-pressed={showPassword}
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? "Hide" : "Show"}
        </button>
      </div>

      {error && (
        <p role="alert" className="auth-form__error">
          {error}
        </p>
      )}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Signing in…" : "Sign in"}
      </button>

      {onSwitchToRegister && (
        <p className="auth-form__switch">
          Need an account?{" "}
          <button type="button" className="link-button" onClick={onSwitchToRegister}>
            Create one
          </button>
        </p>
      )}
    </form>
  );
}

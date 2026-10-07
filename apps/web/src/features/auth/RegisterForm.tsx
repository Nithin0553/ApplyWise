// F01: registration form (UC-1 Register Account).

import { useState } from "react";
import type { FormEvent } from "react";

import { useAuth } from "./AuthContext";

interface RegisterFormProps {
  onRegistered?: () => void;
  onSwitchToLogin?: () => void;
}

export function RegisterForm({ onRegistered, onSwitchToLogin }: RegisterFormProps) {
  const { register, error } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await register({ fullName, email, password });
      onRegistered?.();
    } catch {
      // Error state is surfaced via `error` from useAuth().
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <h2>Create your ApplyWise account</h2>

      <label htmlFor="register-full-name">Full name</label>
      <input
        id="register-full-name"
        name="fullName"
        type="text"
        autoComplete="name"
        required
        value={fullName}
        onChange={(event) => setFullName(event.target.value)}
      />

      <label htmlFor="register-email">Email</label>
      <input
        id="register-email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />

      <label htmlFor="register-password">Password</label>
      <div className="auth-form__password">
        <input
          id="register-password"
          name="password"
          type={showPassword ? "text" : "password"}
          autoComplete="new-password"
          required
          minLength={8}
          aria-describedby="register-password-hint"
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
      <p id="register-password-hint" className="auth-form__hint">
        At least 8 characters, including a letter and a digit.
      </p>

      {error && (
        <p role="alert" className="auth-form__error">
          {error}
        </p>
      )}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating account…" : "Create account"}
      </button>

      {onSwitchToLogin && (
        <p className="auth-form__switch">
          Already have an account?{" "}
          <button type="button" className="link-button" onClick={onSwitchToLogin}>
            Sign in
          </button>
        </p>
      )}
    </form>
  );
}

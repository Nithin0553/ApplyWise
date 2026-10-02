// F01: app-wide authentication state. This is the feature's public
// contract for the rest of the frontend: other features read the current
// user and role through `useAuth()` rather than touching the API client
// or localStorage directly.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { ApiError, fetchCurrentUser, login as loginRequest, registerAccount } from "./api";
import type { LoginInput, RegisterInput, User } from "./types";

const TOKEN_STORAGE_KEY = "applywise.auth.token";

interface AuthContextValue {
  user: User | null;
  /**
   * The current bearer token, for other features' API clients to attach to
   * their own authenticated requests. Treat as opaque and never log it.
   */
  token: string | null;
  /** True while the stored token is being validated on first load. */
  isLoading: boolean;
  error: string | null;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    // localStorage can throw (private browsing, disabled storage); treat
    // as "no session" rather than crashing the app.
    return null;
  }
}

function storeToken(token: string | null): void {
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Best-effort persistence only; the session still works for this tab.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = readStoredToken();
    if (!storedToken) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    fetchCurrentUser(storedToken)
      .then((currentUser) => {
        if (cancelled) return;
        setToken(storedToken);
        setUser(currentUser);
      })
      .catch(() => {
        // Stored token is expired/invalid: clear it rather than retry.
        if (cancelled) return;
        storeToken(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const applySession = useCallback((response: { access_token: string; user: User }) => {
    storeToken(response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  }, []);

  const register = useCallback(
    async (input: RegisterInput) => {
      setError(null);
      try {
        applySession(await registerAccount(input));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Registration failed.");
        throw err;
      }
    },
    [applySession],
  );

  const login = useCallback(
    async (input: LoginInput) => {
      setError(null);
      try {
        applySession(await loginRequest(input));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Login failed.");
        throw err;
      }
    },
    [applySession],
  );

  const logout = useCallback(() => {
    storeToken(null);
    setToken(null);
    setUser(null);
    setError(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, isLoading, error, login, register, logout }),
    [user, token, isLoading, error, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth() must be used within an <AuthProvider>.");
  }
  return context;
}

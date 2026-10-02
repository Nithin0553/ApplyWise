// F01: thin fetch wrapper around the auth endpoints. No other feature
// should call these endpoints directly; they should go through
// AuthContext's `useAuth()` instead, which is this feature's public
// contract for the rest of the app.

import type { AuthResponse, LoginInput, RegisterInput, User } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (Array.isArray(detail)) {
        // FastAPI/Pydantic validation error shape: [{ msg: string, ... }]
        return detail
          .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : null))
          .filter((msg): msg is string => Boolean(msg))
          .join(" ");
      }
    }
  } catch {
    // Response body was not JSON; fall through to the generic message.
  }
  return `Request failed with status ${response.status}.`;
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response), response.status);
  }

  return (await response.json()) as T;
}

export function registerAccount(input: RegisterInput): Promise<AuthResponse> {
  return postJson<AuthResponse>("/auth/register", {
    email: input.email,
    password: input.password,
    full_name: input.fullName,
  });
}

export function login(input: LoginInput): Promise<AuthResponse> {
  return postJson<AuthResponse>("/auth/login", {
    email: input.email,
    password: input.password,
  });
}

export async function fetchCurrentUser(token: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response), response.status);
  }

  return (await response.json()) as User;
}

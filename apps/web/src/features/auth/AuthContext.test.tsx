// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, RequireRole, useAuth } from ".";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const sampleUser = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "jane.seeker@example.com",
  full_name: "Jane Seeker",
  role: "job_seeker" as const,
  is_active: true,
  created_at: "2026-10-01T00:00:00Z",
};

function Probe() {
  const { user, isLoading, login, register, logout, error } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="user-email">{user?.email ?? "none"}</span>
      <span data-testid="error">{error ?? "none"}</span>
      <button
        onClick={() =>
          login({ email: "jane.seeker@example.com", password: "irrelevant1" }).catch(() => {})
        }
      >
        login
      </button>
      <button
        onClick={() =>
          register({
            email: "jane.seeker@example.com",
            password: "irrelevant1",
            fullName: "Jane Seeker",
          }).catch(() => {})
        }
      >
        register
      </button>
      <button onClick={logout}>logout</button>
      <RequireRole allow={["administrator"]} fallback={<span data-testid="gate">hidden</span>}>
        <span data-testid="gate">admin-only content</span>
      </RequireRole>
    </div>
  );
}

describe("AuthProvider / useAuth", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("starts logged out with no stored token", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
    expect(screen.getByTestId("gate")).toHaveTextContent("hidden");
  });

  it("logs in and exposes the returned user", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ access_token: "token-123", token_type: "bearer", user: sampleUser }),
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await act(async () => {
      fireEvent.click(screen.getByText("login"));
    });

    await waitFor(() =>
      expect(screen.getByTestId("user-email")).toHaveTextContent("jane.seeker@example.com"),
    );
    expect(window.localStorage.getItem("applywise.auth.token")).toBe("token-123");
  });

  it("surfaces the server's error message on failed login", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: "Incorrect email or password." }, 401),
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await act(async () => {
      fireEvent.click(screen.getByText("login"));
    });

    await waitFor(() =>
      expect(screen.getByTestId("error")).toHaveTextContent("Incorrect email or password."),
    );
    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
  });

  it("restores the session from a stored token on load", async () => {
    window.localStorage.setItem("applywise.auth.token", "stored-token");
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(jsonResponse(sampleUser));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("user-email")).toHaveTextContent("jane.seeker@example.com"),
    );
  });

  it("clears an invalid stored token instead of retrying forever", async () => {
    window.localStorage.setItem("applywise.auth.token", "expired-token");
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "Could not validate credentials." }, 401));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
    expect(window.localStorage.getItem("applywise.auth.token")).toBeNull();
  });

  it("logout clears the session", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ access_token: "token-123", token_type: "bearer", user: sampleUser }),
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await act(async () => {
      fireEvent.click(screen.getByText("login"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("user-email")).toHaveTextContent("jane.seeker@example.com"),
    );

    await act(async () => {
      fireEvent.click(screen.getByText("logout"));
    });

    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
    expect(window.localStorage.getItem("applywise.auth.token")).toBeNull();
  });
});

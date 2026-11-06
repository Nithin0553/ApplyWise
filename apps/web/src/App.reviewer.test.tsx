// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const mocks = vi.hoisted(() => ({ useAuth: vi.fn() }));

vi.mock("./features/auth", () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => children,
  LoginForm: () => <p>Login form</p>,
  RegisterForm: () => <p>Registration form</p>,
  useAuth: mocks.useAuth,
}));

vi.mock("./features/journey/GuidedJourney", () => ({
  GuidedJourney: () => <main>Job seeker workspace</main>,
}));

vi.mock("./features/sharing", () => ({
  readReviewerShareSecret: (hash: string = window.location.hash) =>
    new URLSearchParams(hash.replace(/^#/, "")).get("share"),
  ReviewerSharePage: ({ secret }: { secret?: string }) => <h2>Reviewer UI: {secret}</h2>,
}));

import { App } from "./App";

const account = (role: "reviewer" | "job_seeker") => ({
  user: {
    id: "reviewer-test-id",
    full_name: "Synthetic User",
    role,
    email: "synthetic@example.org",
    is_active: true,
    created_at: "2026-11-06T00:00:00Z",
  },
  token: "synthetic-token",
  isLoading: false,
  logout: vi.fn(),
});

beforeEach(() => {
  vi.useFakeTimers();
  window.history.replaceState(null, "", "/");
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.clearAllMocks();
  window.history.replaceState(null, "", "/");
});

describe("F14 reviewer access", () => {
  it("consumes the fragment from browser history before revealing it to a reviewer", () => {
    const secret = "synthetic-private-share-secret-123456";
    window.history.replaceState(null, "", `/#share=${secret}`);
    mocks.useAuth.mockReturnValue(account("reviewer"));

    render(<App />);
    expect(window.location.hash).toBe("");
    act(() => { vi.advanceTimersByTime(2400); });

    expect(screen.getByRole("heading", { name: `Reviewer UI: ${secret}` })).toBeInTheDocument();
    expect(screen.queryByText("Job seeker workspace")).not.toBeInTheDocument();
    expect(window.location.href).not.toContain(secret);
  });

  it("does not grant share access to a job seeker, even with a valid-looking link", () => {
    const secret = "synthetic-private-share-secret-654321";
    window.history.replaceState(null, "", `/#share=${secret}`);
    mocks.useAuth.mockReturnValue(account("job_seeker"));

    render(<App />);
    expect(window.location.hash).toBe("");
    act(() => { vi.advanceTimersByTime(2400); });

    expect(screen.getByText("A reviewer account is required.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Reviewer UI/ })).not.toBeInTheDocument();
    expect(window.location.href).not.toContain(secret);
  });

  it("renders the reviewer's manual secret-entry page when no link was provided", () => {
    mocks.useAuth.mockReturnValue(account("reviewer"));
    render(<App />);
    act(() => { vi.advanceTimersByTime(2400); });
    expect(screen.getByRole("heading", { name: "Reviewer UI:" })).toBeInTheDocument();
  });
});

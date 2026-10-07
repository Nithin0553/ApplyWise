// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { AuthProvider } from "../features/auth";
import { Shell } from "./Shell";

afterEach(() => {
  cleanup();
  window.location.hash = "";
});

/**
 * The shell reads the signed-in user for the account menu, so it only ever
 * renders inside the auth provider. With no stored token the provider settles
 * signed-out without calling the network, which is the state exercised here.
 */
function renderShell() {
  return render(
    <AuthProvider>
      <Shell />
    </AuthProvider>,
  );
}

describe("application shell", () => {
  it("opens on the dashboard", () => {
    renderShell();

    expect(screen.getByRole("heading", { name: "ApplyWise" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });

  it("shows an empty state rather than an invented figure", () => {
    renderShell();

    expect(screen.getByText("No approved evidence yet")).toBeInTheDocument();
    expect(screen.getByText("No applications added yet.")).toBeInTheDocument();
  });

  it("navigates between modules", () => {
    renderShell();

    fireEvent.click(screen.getByRole("button", { name: "Evidence" }));

    expect(screen.getByText(/Only approved evidence can be used/i)).toBeInTheDocument();
  });

  it("will not let an unsupported statement be approved", () => {
    renderShell();

    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    const unsupported = screen.getByLabelText(/Improved release quality by 40%/);

    expect(unsupported).toBeDisabled();
  });

  it("hides the account menu when nobody is signed in", () => {
    renderShell();

    expect(screen.queryByRole("button", { name: /account|sign out/i })).not.toBeInTheDocument();
  });

  it("carries no feature numbers or developer notes in the interface", () => {
    renderShell();

    // These leaked into the UI while features were being built. They are
    // internal vocabulary and must not appear on screen.
    expect(document.body.textContent).not.toMatch(/\bF0\d\b/);
    expect(document.body.textContent).not.toMatch(/stubbed|waitlist|prototype/i);
  });
});

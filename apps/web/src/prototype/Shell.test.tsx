// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Shell } from "./Shell";

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

function enterJobDescription(description: string) {
  fireEvent.change(
    screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" }),
    { target: { value: description } },
  );
  fireEvent.click(screen.getByRole("button", { name: /continue/i }));
}

describe("ApplyWise signed-in entry", () => {
  it("opens on the approved page with one input, heading, and basic controls", () => {
    window.location.hash = "";
    render(<Shell />);

    expect(screen.getByRole("heading", { name: "ApplyWise", level: 1 })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Paste your job description to ApplyWise", level: 2 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" }),
    ).toHaveValue("");
    expect(screen.getByText("0 / 6000")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Clear" })).toBeDisabled();
    expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
    expect(screen.queryByText(/We'll use it to tailor/i)).not.toBeInTheDocument();
  });

  it("tracks entered characters and clears the field without leaving the page", () => {
    window.location.hash = "";
    render(<Shell />);

    const textbox = screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" });
    expect(textbox).toHaveAttribute("maxLength", "6000");
    fireEvent.change(textbox, { target: { value: "Python, SQL, and REST testing" } });

    expect(screen.getByText("29 / 6000")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue/i })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(textbox).toHaveValue("");
    expect(screen.getByText("0 / 6000")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();
  });

  it("keeps the pasted job description when continuing to Jobs", async () => {
    window.location.hash = "";
    vi.stubGlobal("scrollTo", vi.fn());
    render(<Shell />);

    const input = screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" });
    fireEvent.change(input, { target: { value: "   " } });
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();

    const description = "We need an analyst who can work with Python and SQL.";
    enterJobDescription(description);

    expect(await screen.findByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#jobs");
    expect(screen.getByDisplayValue(description)).toBeInTheDocument();
    expect(
      screen.getByText("Your job description is ready. Automatic analysis is not yet integrated."),
    ).toBeInTheDocument();
  });

  it("reveals account details and triggers the existing logout callback", () => {
    window.location.hash = "";
    const logout = vi.fn();
    render(<Shell account={{ fullName: "Alex Morgan", email: "alex@example.com", logout }} />);

    expect(screen.getByText("AM")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Profile"));
    expect(screen.getByText("Alex Morgan")).toBeVisible();
    expect(screen.getByText("alex@example.com")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Log out" }));
    expect(logout).toHaveBeenCalledOnce();
  });

  it("keeps the review safety rule after entering the job workflow", async () => {
    window.location.hash = "";
    vi.stubGlobal("scrollTo", vi.fn());
    render(<Shell />);

    enterJobDescription("Software engineer position requiring Python.");
    fireEvent.click(await screen.findByRole("button", { name: "Review" }));

    const unsupported = screen.getByLabelText(/Improved release quality by 40%/);
    expect(unsupported).toBeDisabled();
  });
});

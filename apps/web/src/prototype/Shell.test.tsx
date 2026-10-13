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

describe("prototype shell", () => {
  it("opens with a focused job description field instead of a dashboard", () => {
    window.location.hash = "";
    render(<Shell />);

    expect(screen.getByRole("heading", { name: "ApplyWise" })).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" }),
    ).toHaveValue("");
    expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /continue/i })).not.toBeInTheDocument();
  });

  it("keeps the pasted job description when continuing to Jobs", async () => {
    window.location.hash = "";
    vi.stubGlobal("scrollTo", vi.fn());
    render(<Shell />);

    fireEvent.change(
      screen.getByRole("textbox", { name: "Paste your job description to ApplyWise" }),
      { target: { value: "   " } },
    );
    expect(screen.queryByRole("button", { name: /continue/i })).not.toBeInTheDocument();

    const description = "We need an analyst who can work with Python and SQL.";
    enterJobDescription(description);

    expect(await screen.findByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#jobs");
    expect(screen.getByDisplayValue(description)).toBeInTheDocument();
    expect(
      screen.getByText("Your job description is ready. Automatic analysis is not yet integrated."),
    ).toBeInTheDocument();
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

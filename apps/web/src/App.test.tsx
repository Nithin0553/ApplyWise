// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("shows the sign-in screen when nobody is signed in", async () => {
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Sign in to ApplyWise" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Explore Demo" })).toBeInTheDocument();
  });

  it("opens, navigates, and exits an offline demo without authenticating or calling the API", async () => {
    window.localStorage.clear();
    const api = vi.fn();
    vi.stubGlobal("fetch", api);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Explore Demo" }));

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText(/You are exploring sample data/)).toBeInTheDocument();
    expect(screen.getByText("Sample overview")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Tailoring" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));
    expect(screen.getByText(/Sample results only/)).toBeInTheDocument();
    expect(screen.getByText(/sample data \(offline\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cover Letter" }));
    fireEvent.click(screen.getByRole("button", { name: "Draft letter" }));
    expect(screen.getByText(/Sample letter preview/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Resume" }));
    expect(screen.getByText("Alex Morgan")).toBeInTheDocument();

    expect(api).not.toHaveBeenCalled();
    expect(window.localStorage.getItem("applywise.auth.token")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Exit demo" }));
    expect(screen.getByRole("heading", { name: "Sign in to ApplyWise" })).toBeInTheDocument();
    expect(screen.queryByText(/You are exploring sample data/)).not.toBeInTheDocument();
  });
});

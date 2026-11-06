// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";

afterEach(() => cleanup());

describe("App", () => {
  it("shows the welcome animation then the blue-green themed original login", async () => {
    render(<App />);
    expect(screen.getByRole("main", { name: "ApplyWise welcome" })).toBeInTheDocument();

    expect(
      await screen.findByRole("heading", { name: "Sign in to ApplyWise" }, { timeout: 4000 }),
    ).toBeInTheDocument();
    const brand = screen.getByRole("heading", { name: "ApplyWise", level: 1 });
    expect(brand).toHaveClass("aw-auth-wordmark");
    expect(brand.querySelector(".aw-auth-wordmark-light")).toHaveAttribute("data-text", "ApplyWise");
    expect(brand.closest(".aw-auth-shell")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("autocomplete", "email");
  }, 6000);

  it("keeps registration and sign-in accessible from the same themed page", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Sign in to ApplyWise" }, { timeout: 4000 });

    fireEvent.click(screen.getByRole("button", { name: "Create one" }));
    expect(screen.getByRole("heading", { name: "Create your ApplyWise account" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Full name" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByRole("heading", { name: "Sign in to ApplyWise" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "ApplyWise", level: 1 })).toBeInTheDocument();
  }, 6000);
});

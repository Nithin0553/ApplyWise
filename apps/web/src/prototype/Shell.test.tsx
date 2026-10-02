// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Shell } from "./Shell";

afterEach(cleanup);

describe("prototype shell", () => {
  it("opens on the landing page", () => {
    render(<Shell />);

    expect(screen.getByRole("heading", { name: "ApplyWise" })).toBeInTheDocument();
    expect(screen.getByText(/traceable/i)).toBeInTheDocument();
  });

  it("navigates between modules", () => {
    render(<Shell />);

    fireEvent.click(screen.getByRole("button", { name: "Evidence" }));

    expect(screen.getByText(/Only approved evidence can be used/i)).toBeInTheDocument();
  });

  it("will not let an unsupported statement be approved", () => {
    render(<Shell />);

    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    const unsupported = screen.getByLabelText(/Improved release quality by 40%/);

    expect(unsupported).toBeDisabled();
  });
});

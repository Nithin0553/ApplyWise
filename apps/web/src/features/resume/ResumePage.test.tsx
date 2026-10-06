// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResumePage } from "./ResumePage";

describe("ResumePage", () => {
  it("updates the selected template when the user changes it", () => {
    render(<ResumePage />);

    const selector = screen.getByRole("combobox", {
      name: "Resume template",
    });

    expect(selector).toHaveValue("standard");

    fireEvent.change(selector, { target: { value: "compact" } });

    expect(selector).toHaveValue("compact");
    expect(
      screen.getByText("Selected template: Compact"),
    ).toBeInTheDocument();
  });
});
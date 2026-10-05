// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvidenceForm } from "./EvidenceForm";

afterEach(cleanup);

describe("EvidenceForm", () => {
  it("submits normalized evidence values", () => {
    const onSubmit = vi.fn();
    render(<EvidenceForm onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Evidence type"), {
      target: { value: "skill" },
    });
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "  Python backend development  " },
    });
    fireEvent.change(screen.getByLabelText("Organization"), {
      target: { value: "  Example Labs  " },
    });
    fireEvent.change(screen.getByLabelText("Skill name"), {
      target: { value: "  Python  " },
    });
    fireEvent.change(screen.getByLabelText("Proficiency"), {
      target: { value: "  Advanced  " },
    });
    fireEvent.change(screen.getByLabelText("Start date"), {
      target: { value: "2024-01-01" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save evidence" }));

    expect(onSubmit).toHaveBeenCalledWith({
      evidenceType: "skill",
      title: "Python backend development",
      organization: "Example Labs",
      role: "",
      location: "",
      description: "",
      skillName: "Python",
      proficiency: "Advanced",
      credential: "",
      url: "",
      startDate: "2024-01-01",
      endDate: "",
      source: "",
    });
  });

  it("rejects an end date earlier than the start date", () => {
    const onSubmit = vi.fn();
    render(<EvidenceForm onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Synthetic role" },
    });
    fireEvent.change(screen.getByLabelText("Start date"), {
      target: { value: "2026-06-01" },
    });
    fireEvent.change(screen.getByLabelText("End date"), {
      target: { value: "2026-05-01" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save evidence" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "End date cannot be earlier than start date.",
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("warns that editing approved evidence can revoke approval", () => {
    render(
      <EvidenceForm
        initialValues={{ title: "Approved evidence" }}
        approvalWillBeRevoked
        submitLabel="Save changes"
        onSubmit={() => undefined}
      />,
    );

    expect(screen.getByRole("note")).toHaveTextContent(
      "return it to unconfirmed status",
    );
  });
});

// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApplicationForm } from "./ApplicationForm";

afterEach(cleanup);

describe("ApplicationForm", () => {
  it("submits normalized application metadata", () => {
    const onSubmit = vi.fn();
    render(<ApplicationForm onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Company"), {
      target: { value: "  Example Robotics  " },
    });
    fireEvent.change(screen.getByLabelText("Role title"), {
      target: { value: "  Software Engineer  " },
    });
    fireEvent.change(screen.getByLabelText("Location"), {
      target: { value: "Dallas, TX" },
    });
    fireEvent.change(screen.getByLabelText("Job link"), {
      target: { value: "https://example.invalid/jobs/456" },
    });
    fireEvent.change(screen.getByLabelText("Source"), {
      target: { value: "Career fair" },
    });
    fireEvent.change(screen.getByLabelText("Applied date"), {
      target: { value: "2026-10-01" },
    });
    fireEvent.change(screen.getByLabelText("Next action date"), {
      target: { value: "2026-10-08" },
    });
    fireEvent.change(screen.getByLabelText("Notes"), {
      target: { value: "  Follow up with recruiter.  " },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save application" }));

    expect(onSubmit).toHaveBeenCalledWith({
      companyName: "Example Robotics",
      roleTitle: "Software Engineer",
      location: "Dallas, TX",
      jobUrl: "https://example.invalid/jobs/456",
      source: "Career fair",
      notes: "Follow up with recruiter.",
      appliedOn: "2026-10-01",
      nextActionOn: "2026-10-08",
    });
  });

  it("renders supplied values for editing", () => {
    render(
      <ApplicationForm
        initialValues={{
          companyName: "Synthetic Systems",
          roleTitle: "Backend Engineer",
          notes: "Existing synthetic note",
        }}
        submitLabel="Update application"
        onSubmit={() => undefined}
      />,
    );

    expect(screen.getByLabelText("Company")).toHaveValue("Synthetic Systems");
    expect(screen.getByLabelText("Role title")).toHaveValue("Backend Engineer");
    expect(screen.getByLabelText("Notes")).toHaveValue("Existing synthetic note");
    expect(
      screen.getByRole("button", { name: "Update application" }),
    ).toBeInTheDocument();
  });

  it("exposes cancel without submitting", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    render(<ApplicationForm onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onCancel).toHaveBeenCalledOnce();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

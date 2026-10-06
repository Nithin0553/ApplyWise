// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApplicationTracker } from "./ApplicationTracker";
import type { ApplicationSummary, ResumeVersionSummary } from "./types";

afterEach(cleanup);

const applications: readonly ApplicationSummary[] = [
  {
    id: "app-1",
    companyName: "Example Robotics",
    roleTitle: "Software Engineer",
    status: "applied",
    location: "Dallas, TX",
    appliedOn: "2026-10-01",
    nextActionOn: "2026-10-08",
    versionCount: 2,
  },
  {
    id: "app-2",
    companyName: "Synthetic Systems",
    roleTitle: "Backend Engineer",
    status: "draft",
    versionCount: 0,
  },
];

const versions: readonly ResumeVersionSummary[] = [
  {
    id: "version-1",
    versionNumber: 1,
    createdAt: "2026-10-01T12:00:00Z",
    statementCount: 4,
  },
  {
    id: "version-2",
    versionNumber: 2,
    createdAt: "2026-10-02T12:00:00Z",
    statementCount: 5,
  },
];

describe("ApplicationTracker", () => {
  it("renders the selected application and resume version history", () => {
    render(
      <ApplicationTracker
        applications={applications}
        selectedApplicationId="app-1"
        resumeVersions={versions}
        onSelectApplication={() => undefined}
      />,
    );

    expect(screen.getByRole("heading", { name: "Example Robotics" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Version 1/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Version 2/ })).toBeInTheDocument();
  });

  it("notifies the parent when another application is selected", () => {
    const onSelectApplication = vi.fn();
    render(
      <ApplicationTracker
        applications={applications}
        selectedApplicationId="app-1"
        resumeVersions={versions}
        onSelectApplication={onSelectApplication}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Synthetic Systems/ }));

    expect(onSelectApplication).toHaveBeenCalledWith("app-2");
  });

  it("offers only valid forward status changes", () => {
    const onStatusChange = vi.fn();
    render(
      <ApplicationTracker
        applications={applications}
        selectedApplicationId="app-1"
        resumeVersions={versions}
        onSelectApplication={() => undefined}
        onStatusChange={onStatusChange}
      />,
    );

    const select = screen.getByLabelText("Update status for Example Robotics");
    expect(screen.queryByRole("option", { name: "Draft" })).not.toBeInTheDocument();

    fireEvent.change(select, { target: { value: "interviewing" } });

    expect(onStatusChange).toHaveBeenCalledWith("app-1", "interviewing");
  });

  it("exposes edit for the selected application", () => {
    const onEditApplication = vi.fn();
    render(
      <ApplicationTracker
        applications={applications}
        selectedApplicationId="app-1"
        resumeVersions={versions}
        onSelectApplication={() => undefined}
        onEditApplication={onEditApplication}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Edit application" }));

    expect(onEditApplication).toHaveBeenCalledWith("app-1");
  });

  it("disables status changes for terminal applications", () => {
    const terminalApplication: ApplicationSummary = {
      id: "app-terminal",
      companyName: "Closed Example",
      roleTitle: "Engineer",
      status: "rejected",
      versionCount: 1,
    };

    render(
      <ApplicationTracker
        applications={[terminalApplication]}
        selectedApplicationId={terminalApplication.id}
        resumeVersions={[]}
        onSelectApplication={() => undefined}
        onStatusChange={() => undefined}
      />,
    );

    expect(screen.getByLabelText("Update status for Closed Example")).toBeDisabled();
  });

  it("shows the empty and unselected states", () => {
    const { rerender } = render(
      <ApplicationTracker
        applications={[]}
        resumeVersions={[]}
        onSelectApplication={() => undefined}
      />,
    );

    expect(screen.getByText("No applications tracked yet.")).toBeInTheDocument();
    expect(screen.getByText("Select an application to view its details.")).toBeInTheDocument();

    rerender(
      <ApplicationTracker
        applications={applications}
        resumeVersions={[]}
        onSelectApplication={() => undefined}
      />,
    );

    expect(screen.getByText("Select an application to view its details.")).toBeInTheDocument();
  });
});

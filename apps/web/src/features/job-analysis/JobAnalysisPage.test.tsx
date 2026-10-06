// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { JobAnalysisPage } from "./JobAnalysisPage";

const result = {
  schema_version: "1.0", document_id: "sample", warnings: [],
  requirements: [{ id: "JR-1", text: "Python required", categories: ["skill"], importance: "Critical",
    importance_basis: "explicit", source: { text: "Python required", start: 0, end: 15, line: 1, section: null },
    experience: null, needs_review: false, review_reasons: [],
  }],
};
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("F04 job analysis review", () => {
  it("disables empty submissions and loads a sample", () => {
    render(<JobAnalysisPage />);
    expect(screen.getByRole("button", { name: "Analyze requirements" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Load sample posting" }));
    expect((screen.getByLabelText("Job description") as HTMLTextAreaElement).value).toContain("Required qualifications");
  });
  it("submits text and displays requirements with exact source context", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => result });
    vi.stubGlobal("fetch", fetchMock);
    render(<JobAnalysisPage />);
    fireEvent.change(screen.getByLabelText("Job description"), { target: { value: "Python required" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze requirements" }));
    expect(await screen.findByText("Critical")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/f04/analyze", expect.objectContaining({ body: JSON.stringify({ job_description: "Python required" }) }));
    fireEvent.click(screen.getByRole("button", { name: "View source for line 1" }));
    expect(screen.getByRole("region", { name: "Source context" })).toHaveTextContent("Python required");
    fireEvent.change(screen.getByLabelText("Job description"), { target: { value: "SQL" } });
    expect(screen.getByText(/The input has changed/)).toBeInTheDocument();
  });
  it("shows validation errors and no stale results", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, json: async () => ({ detail: "No identifiable job requirements found" }) }));
    render(<JobAnalysisPage />);
    fireEvent.change(screen.getByLabelText("Job description"), { target: { value: "Hello there" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze requirements" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No identifiable job requirements");
    expect(screen.queryByText("Extracted requirements")).not.toBeInTheDocument();
  });
});

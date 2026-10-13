import { useEffect, useState, type ReactElement } from "react";

import "./softly.css";
import { ApprovalContext, approvableIds } from "./store";
import { CoverLetterPage } from "./pages/CoverLetterPage";
import { EvidencePage } from "./pages/EvidencePage";
import { JobDescriptionEntryPage } from "./pages/JobDescriptionEntryPage";
import { JobsPage } from "./pages/JobsPage";
import { MatchPage } from "./pages/MatchPage";
import { ResumePage } from "./pages/ResumePage";
import { ReviewPage } from "./pages/ReviewPage";
import { TailoringPage } from "./pages/TailoringPage";
import { TrackerPage } from "./pages/TrackerPage";

const ROUTES = [
  { id: "home", label: "Home" },
  { id: "evidence", label: "Evidence" },
  { id: "jobs", label: "Jobs" },
  { id: "match", label: "Match" },
  { id: "tailor", label: "Tailor" },
  { id: "review", label: "Review" },
  { id: "cover", label: "Cover letter" },
  { id: "resume", label: "Resume" },
  { id: "tracker", label: "Tracker" },
] as const;

export type RouteId = (typeof ROUTES)[number]["id"];

/** Hash routing, so the prototype needs no router dependency. */
function useRoute(): [RouteId, (next: RouteId) => void] {
  const read = (): RouteId => {
    const raw = window.location.hash.replace("#", "") as RouteId;
    return ROUTES.some((route) => route.id === raw) ? raw : "home";
  };

  const [route, setRoute] = useState<RouteId>(read);

  useEffect(() => {
    const onChange = () => setRoute(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const go = (next: RouteId) => {
    window.location.hash = next;
    setRoute(next);
    window.scrollTo({ top: 0 });
  };

  return [route, go];
}

export interface ShellAccount {
  fullName: string;
  email: string;
  logout: () => void;
}

export function Shell({ account }: { account?: ShellAccount } = {}) {
  const [route, go] = useRoute();
  const [jobDescription, setJobDescription] = useState("");
  const [approvedIds, setApprovedIds] = useState<string[]>(approvableIds().slice(0, 2));

  const approvals = {
    approvedIds,
    toggle: (id: string) =>
      setApprovedIds((current) =>
        current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
      ),
  };

  const pages: Record<Exclude<RouteId, "home">, ReactElement> = {
    evidence: <EvidencePage go={go} />,
    jobs: <JobsPage go={go} initialDescription={jobDescription} onDescriptionChange={setJobDescription} />,
    match: <MatchPage go={go} />,
    tailor: <TailoringPage go={go} />,
    review: <ReviewPage go={go} />,
    cover: <CoverLetterPage go={go} />,
    resume: <ResumePage go={go} />,
    tracker: <TrackerPage go={go} />,
  };

  if (route === "home") {
    return (
      <ApprovalContext.Provider value={approvals}>
        <div className="sf sf--job-entry">
          <header className="sf-jd-header">
            <h1 className="sf-jd-brand">ApplyWise</h1>
            {account && (
              <div className="sf-jd-header-actions">
                <span className="sf-jd-avatar" aria-hidden="true">
                  {(account.fullName.trim().split(/\s+/).slice(0, 2).map((part) => part.charAt(0)).join("") || "?").toUpperCase()}
                </span>
                <details className="sf-jd-profile">
                  <summary>Profile</summary>
                  <div className="sf-jd-profile-popover">
                    <strong>{account.fullName}</strong>
                    <span>{account.email}</span>
                  </div>
                </details>
                <span className="sf-jd-header-separator" aria-hidden="true" />
                <button type="button" className="sf-jd-logout" onClick={() => {
                  window.location.hash = "";
                  account.logout();
                }}>
                  Log out
                </button>
              </div>
            )}
          </header>
          <JobDescriptionEntryPage
            onContinue={(description) => {
              setJobDescription(description);
              go("jobs");
            }}
          />
        </div>
      </ApprovalContext.Provider>
    );
  }

  return (
    <ApprovalContext.Provider value={approvals}>
    <div className="sf">
      <div className="sf-grain" aria-hidden="true" />
      <h1 className="sf-sr">ApplyWise</h1>

      <nav className="sf-nav" aria-label="Main">
        <span className="sf-logo">
          <span className="sf-logo-dot" aria-hidden="true" />
          ApplyWise
        </span>
        <div className="sf-navlinks">
          {ROUTES.map((item) => (
            <button
              key={item.id}
              type="button"
              className="sf-navlink"
              aria-current={route === item.id ? "page" : undefined}
              onClick={() => go(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      {pages[route]}
    </div>
    </ApprovalContext.Provider>
  );
}

export interface PageProps {
  go: (next: RouteId) => void;
}

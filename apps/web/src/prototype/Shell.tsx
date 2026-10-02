import { useEffect, useState, type ReactElement } from "react";

import "./softly.css";
import { ApprovalContext, approvableIds } from "./store";
import { CoverLetterPage } from "./pages/CoverLetterPage";
import { EvidencePage } from "./pages/EvidencePage";
import { HomePage } from "./pages/HomePage";
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

export function Shell() {
  const [route, go] = useRoute();
  const [approvedIds, setApprovedIds] = useState<string[]>(approvableIds().slice(0, 2));

  const approvals = {
    approvedIds,
    toggle: (id: string) =>
      setApprovedIds((current) =>
        current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
      ),
  };

  const pages: Record<RouteId, ReactElement> = {
    home: <HomePage go={go} />,
    evidence: <EvidencePage go={go} />,
    jobs: <JobsPage go={go} />,
    match: <MatchPage go={go} />,
    tailor: <TailoringPage go={go} />,
    review: <ReviewPage go={go} />,
    cover: <CoverLetterPage go={go} />,
    resume: <ResumePage go={go} />,
    tracker: <TrackerPage go={go} />,
  };

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
